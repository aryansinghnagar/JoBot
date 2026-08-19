import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jobot.adapters import AdapterRegistry, SiteAdapter
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.llm.router import ModelRouter
from jobot.models.domain import Application, ApplicationStatus, TrustLevel
from jobot.obs.application_md_logger import ApplicationMarkdownLogger
from jobot.policy.engine import PolicyEngine
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault

logger = logging.getLogger(__name__)

# Statuses that count toward the campaign goal (terminal success at submit).
_SUCCESS_STATUSES = {"verified", "submitted"}


def get_adapter(site: str) -> SiteAdapter:
    return AdapterRegistry.get_adapter(site)


class ContinuousCampaignRunner:
    """
    Round-Robin Continuous Campaign Runner.

    Composes the Phase 3 ApplyOrchestrator (saga + idempotency + grounding) —
    the single source of truth for apply — with the discovery engine and the
    PolicyEngine daily caps. Halts when the ModelRouter LLM daily cost budget
    is exhausted (cost-gated campaign).
    """

    def __init__(
        self,
        root_dir: Path | None = None,
        orchestrator: ApplyOrchestrator | None = None,
        router: ModelRouter | None = None,
        discovery_factory: Callable[[str], Any] | None = None,
    ):
        if root_dir is None:
            root_dir = Path.cwd()
        self.root_dir = root_dir
        self.md_logger = ApplicationMarkdownLogger(root_dir=root_dir)
        self.db = DatabaseManager()
        self.vault = CredentialVault()
        self.policy_engine = PolicyEngine()
        self.orchestrator = orchestrator or ApplyOrchestrator(self.db)
        self.router = router or ModelRouter()
        self.discovery_factory = discovery_factory or (
            lambda portal: JobDiscoveryEngine(active_portals=[portal])
        )

    def _cost_gate_open(self) -> bool:
        """True when the LLM daily budget is exhausted (local providers exempt)."""
        return self.router.current_spent_usd >= self.router.daily_budget_usd

    async def run_continuous_campaign(
        self,
        goal_count: int = 1000,
        min_match: float = 0.20,
        auto_submit: bool = False,
        max_iterations: int = 2000,
    ) -> int:
        """Run a round-robin campaign across all known portals.

        Audit fix JOB-SEC-001 / JOB-ARC-003 / JOB-UX-005: the default for
        ``auto_submit`` is now ``False`` (supervised), aligning the runtime
        default with decision D15 in ``SECURITY.md`` ("submission autonomy is
        human-by-default"). Callers who want autonomous submission must pass
        ``auto_submit=True`` explicitly. The inter-iteration sleep is also
        raised to a randomized 5–15s courtesy window to respect portal ToS.
        """
        import random

        profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
        if not profile_path.exists():
            logger.error("No candidate profile found. Initialize profile first.")
            return 0

        p = self.vault.load_encrypted_profile(profile_path)

        target_titles = [
            "AI/ML Engineer",
            "Data Scientist",
            "Data Analyst",
            "Software Developer",
            "Frontend Developer",
            "Backend Developer",
            "Full-Stack Developer",
        ]

        portals = [
            "naukri",
            "linkedin",
            "indeed",
            "greenhouse",
            "lever",
            "workday",
            "glassdoor",
            "instahyre",
            "cutshort",
            "wellfound",
            "shine",
            "foundit",
            "hirist",
            "ziprecruiter",
            "smartrecruiters",
        ]

        total_submitted = 0
        portal_index = 0

        print(
            f"=== Starting JoBot High-Throughput Campaign (Goal: {goal_count}+ Apps | Min Match: {int(min_match * 100)}%) ==="
        )

        for _ in range(max_iterations):
            if total_submitted >= goal_count:
                break

            # LLM cost gate: halt the campaign when today's LLM budget is spent.
            if self._cost_gate_open():
                logger.warning(
                    "[COST GATE] LLM daily budget exhausted ($%.2f/$%.2f); halting campaign",
                    self.router.current_spent_usd,
                    self.router.daily_budget_usd,
                )
                print(
                    f"\n[STOP] LLM daily cost budget exhausted "
                    f"(${self.router.current_spent_usd:.2f}/${self.router.daily_budget_usd:.2f})."
                )
                break

            # Round-Robin Portal Selection
            selected_portal = portals[portal_index % len(portals)]
            portal_index += 1

            # Select target role for this iteration
            title = target_titles[total_submitted % len(target_titles)]

            try:
                discovery = self.discovery_factory(selected_portal)
                matches = await discovery.discover_matching_jobs(
                    p, target_title=title, limit_per_portal=1, min_match_threshold=min_match
                )
            except Exception as exc:
                logger.error(f"[DISCOVERY ERROR] Error searching portal {selected_portal}: {exc}")
                matches = []

            if not matches:
                # Brief backoff when a portal returns no matches. Stays short
                # because the round-robin already rotates to the next portal
                # on the next iteration — this is just to avoid hot-looping
                # against a portal that is currently throttling us.
                await asyncio.sleep(random.uniform(1.0, 3.0))
                continue

            for match in matches:
                if total_submitted >= goal_count:
                    break

                try:
                    job = match.posting

                    # Policy Enforcement Check (daily caps, truthfulness rules)
                    daily_count = self.db.get_daily_application_count(job.site)
                    intent_app = Application(
                        application_id="intent_check",
                        job_id=job.job_id,
                        site=job.site,
                        idempotency_key=f"intent_{job.job_id}",
                        status=ApplicationStatus.INTENT,
                        trust_level=TrustLevel.AUTONOMOUS if auto_submit else TrustLevel.SUPERVISED,
                    )
                    policy_res = self.policy_engine.check_application_policy(
                        job, p, intent_app, daily_submitted_count=daily_count
                    )
                    if not policy_res.allowed:
                        logger.warning(
                            f"[POLICY BLOCKED] Skipping {job.title} at {job.company}: {policy_res.blocking_reason}"
                        )
                        continue

                    # Apply via the orchestrator: saga + idempotency + grounding gate.
                    apply_result = await self.orchestrator.apply(job, p, auto_approve=auto_submit)
                    status = (apply_result.app_status or "").lower()
                    if status in _SUCCESS_STATUSES:
                        total_submitted += 1

                    # Audit record: log.md at project root.
                    app = None
                    if apply_result.application_id:
                        app = self.db.get_application(apply_result.application_id)
                    if app is None:
                        app = Application(
                            application_id=apply_result.application_id or "unknown",
                            job_id=job.job_id,
                            site=job.site,
                            idempotency_key=f"runner-{job.job_id}",
                            status=ApplicationStatus[status.upper()]
                            if status
                            else ApplicationStatus.SUBMITTED,
                            trust_level=TrustLevel.AUTONOMOUS
                            if auto_submit
                            else TrustLevel.SUPERVISED,
                        )
                    self.md_logger.log_submission(app, job, match_score=match.match_score)

                    print(
                        f"[{total_submitted}/{goal_count}] [{job.site.upper()}] {job.title} at {job.company} | Match: {int(match.match_score * 100)}% -> {status.upper()}"
                    )
                except Exception as exc:
                    logger.error(
                        f"[RUNNER ERROR] Failed processing match for portal {selected_portal}: {exc}"
                    )

                # Audit fix JOB-UX-005: raise inter-iteration sleep from 0.05s
                # to a randomized 5–15s window. The previous 0.05s sleep implied
                # ~20 applications/second throughput — well below any reasonable
                # rate-limit courtesy floor and likely to trip anti-bot heuristics
                # on LinkedIn, Naukri, Workday, and Indeed. A small jitter also
                # prevents request-pattern fingerprinting.
                await asyncio.sleep(random.uniform(5.0, 15.0))

        print(f"\n[OK] Continuous Campaign Reached Target Goal of {total_submitted} Applications!")
        return total_submitted
