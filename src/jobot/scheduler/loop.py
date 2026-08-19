"""Loop executor — 4-mode scheduler (plan.md Chapter 20).

Modes: scan-only | apply-only | digest-only | full-loop.

Composes the Phase 3 ApplyOrchestrator (single source of truth for apply)
with the discovery engine, PolicyEngine daily caps, and the digest generator.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.digest.generator import DigestGenerator
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    TrustLevel,
    UserProfile,
)
from jobot.notify.email import EmailSender
from jobot.policy.engine import PolicyEngine
from jobot.storage.db import DatabaseManager

logger = logging.getLogger("jobot.loop")

MODES = ("scan-only", "apply-only", "digest-only", "full-loop")

TERMINAL_STATUSES = {
    ApplicationStatus.VERIFIED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.FAILED,
    ApplicationStatus.CIRCUIT_OPEN,
    ApplicationStatus.CANCELLED,
    ApplicationStatus.BLOCKED,
}


@dataclass
class LoopResult:
    mode: str
    discovered: int = 0
    applied: int = 0
    submitted: int = 0
    verified: int = 0
    rejected: int = 0
    failed: int = 0
    blocked: int = 0
    digest_sent: bool = False
    notes: list[str] = field(default_factory=list)


class LoopExecutor:
    """Runs a single scheduler loop iteration in one of four modes."""

    def __init__(
        self,
        db: DatabaseManager | None = None,
        orchestrator: ApplyOrchestrator | None = None,
        policy: PolicyEngine | None = None,
        discovery: Any | None = None,
        digest: DigestGenerator | None = None,
        email: EmailSender | None = None,
    ) -> None:
        self.db = db or DatabaseManager()
        self.orchestrator = orchestrator or ApplyOrchestrator(self.db)
        self.policy = policy or PolicyEngine()
        from jobot.discovery.engine import JobDiscoveryEngine

        self.discovery = discovery or JobDiscoveryEngine()
        self.digest = digest
        self.email = email or EmailSender()

    async def _scan(
        self, profile: UserProfile, target_title: str, limit_per_portal: int, min_match: float
    ) -> list[Any]:
        matches = await self.discovery.discover_matching_jobs(
            profile,
            target_title=target_title,
            limit_per_portal=limit_per_portal,
            min_match_threshold=min_match,
        )
        for m in matches:
            try:
                self.db.save_job_posting(m.posting)
            except Exception:  # noqa: BLE001
                logger.warning("loop: failed to persist job %s", m.posting.job_id)
        return matches

    def _daily_submitted(self, site: str) -> int:
        return self.db.get_daily_application_count(site)

    async def _apply_loop(
        self, profile: UserProfile, matches: list[Any], max_apply: int, auto_approve: bool
    ) -> tuple[LoopResult, list[str]]:
        res = LoopResult(mode="apply")
        notes: list[str] = []
        for m in matches[:max_apply]:
            job: JobPosting = m.posting
            daily = self._daily_submitted(job.site)
            stub = Application(
                application_id=f"loop-{job.job_id}",
                job_id=job.job_id,
                site=job.site,
                idempotency_key=f"loop-{job.job_id}",
                status=ApplicationStatus.INTENT,
                trust_level=TrustLevel.AUTONOMOUS if auto_approve else TrustLevel.SUPERVISED,
            )
            pr = self.policy.check_application_policy(job, profile, stub, daily)
            if not pr.allowed:
                res.blocked += 1
                if pr.blocking_reason and "Daily limit" in str(pr.blocking_reason):
                    notes.append(f"daily cap reached for {job.site}; stopping apply loop")
                    break
                notes.append(f"{job.title} blocked by policy: {pr.blocking_reason}")
                continue

            apply_result = await self.orchestrator.apply(
                job, profile, auto_approve=auto_approve, dry_run=False
            )
            res.applied += 1
            status = apply_result.app_status
            if status == "verified":
                res.verified += 1
            elif status == "rejected":
                res.rejected += 1
            elif status in TERMINAL_STATUSES:
                res.failed += 1
            elif status == "pending_approval":
                # Supervised: awaiting human OK — not a failure.
                pass
            else:
                res.submitted += 1

            if not pr.allowed or self._daily_cap_hit(job.site, daily):
                notes.append(f"site {job.site} daily cap hit; stopping")
                break
        return res, notes

    def _daily_cap_hit(self, site: str, prior_count: int) -> bool:
        limit = {
            "naukri": 150,
            "linkedin": 100,
            "indeed": 100,
            "greenhouse": 150,
            "lever": 150,
            "workday": 100,
            "mock_ats": 200,
        }.get(site, 20)
        return self._daily_submitted(site) >= limit

    async def run(
        self,
        mode: str,
        profile: UserProfile,
        target_title: str = "Python Developer",
        max_apply: int = 10,
        auto_approve: bool = False,
        min_match: float = 0.20,
        limit_per_portal: int = 5,
    ) -> LoopResult:
        if mode not in MODES:
            raise ValueError(f"unknown loop mode '{mode}'; one of {MODES}")

        res = LoopResult(mode=mode)
        notes: list[str] = []

        matches: list[Any] = []
        if mode in ("scan-only", "apply-only", "full-loop"):
            matches = await self._scan(profile, target_title, limit_per_portal, min_match)
            res.discovered = len(matches)
            notes.append(f"discovered {len(matches)} jobs at match>={min_match}")

        if mode in ("apply-only", "full-loop"):
            apply_res, apply_notes = await self._apply_loop(
                profile, matches, max_apply, auto_approve
            )
            res.submitted += apply_res.submitted
            res.verified += apply_res.verified
            res.rejected += apply_res.rejected
            res.failed += apply_res.failed
            res.blocked += apply_res.blocked
            res.applied = apply_res.applied
            notes.extend(apply_notes)

        if mode in ("digest-only", "full-loop"):
            sent = await self._digest_step()
            res.digest_sent = sent
            notes.append("digest sent" if sent else "digest generated (dry-run/not configured)")

        res.notes = notes
        logger.info("loop %s: %s", mode, res)
        return res

    async def _digest_step(self) -> bool:
        if self.digest is None:
            self.digest = DigestGenerator(self.db)
        digest = self.digest.generate()
        ok, _msg = self.email.send(digest.subject, digest.html, body_text=digest.text)
        return bool(ok)
