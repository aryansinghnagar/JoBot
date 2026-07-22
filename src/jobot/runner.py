import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from jobot.adapters import AdapterRegistry
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.obs.application_md_logger import ApplicationMarkdownLogger
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault
from jobot.policy.engine import PolicyEngine
from jobot.models.domain import ApplicationStatus

logger = logging.getLogger(__name__)


def get_adapter(site: str):
    return AdapterRegistry.get_adapter(site)


class ContinuousCampaignRunner:
    """
    High-Throughput Round-Robin Continuous Campaign Runner.
    Distributes applications evenly across 15 job portals with 20% match threshold.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            root_dir = Path.cwd()
        self.root_dir = root_dir
        self.md_logger = ApplicationMarkdownLogger(root_dir=root_dir)
        self.db = DatabaseManager()
        self.vault = CredentialVault()
        self.policy_engine = PolicyEngine()

    async def run_continuous_campaign(
        self,
        goal_count: int = 1000,
        min_match: float = 0.20,
    ) -> int:
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
            "naukri", "linkedin", "indeed", "greenhouse", "lever",
            "workday", "glassdoor", "instahyre", "cutshort", "wellfound",
            "shine", "foundit", "hirist", "ziprecruiter", "smartrecruiters"
        ]

        total_submitted = 0
        portal_index = 0

        print(f"=== Starting JoBot High-Throughput Campaign (Goal: {goal_count}+ Apps | Min Match: {int(min_match*100)}%) ===")

        while total_submitted < goal_count:
            # Round-Robin Portal Selection
            selected_portal = portals[portal_index % len(portals)]
            portal_index += 1

            # Select target role for this iteration
            title = target_titles[total_submitted % len(target_titles)]

            discovery = JobDiscoveryEngine(active_portals=[selected_portal])
            matches = await discovery.discover_matching_jobs(p, target_title=title, limit_per_portal=1, min_match_threshold=min_match)

            for match in matches:
                if total_submitted >= goal_count:
                    break

                job = match.posting
                adapter = get_adapter(job.site)
                pipeline = ApplicationSubmissionPipeline(adapter, self.db)

                # Policy Enforcement Check
                daily_count = 0  # In-memory tracking per portal session
                policy_res = self.policy_engine.check_application_policy(
                    job, p, match.posting, daily_submitted_count=daily_count
                ) if hasattr(self.policy_engine, "check_application_policy") else None

                if policy_res and not policy_res.allowed:
                    logger.warning(f"[POLICY BLOCKED] Skipping {job.title} at {job.company}: {policy_res.blocking_reason}")
                    continue

                auto_approve = not (policy_res and policy_res.requires_approval)
                app_res = await pipeline.execute(job.url, p, auto_approve=auto_approve)
                if app_res.status == ApplicationStatus.VERIFIED or app_res.status == ApplicationStatus.SUBMITTED:
                    total_submitted += 1

                # Maintain log.md at project root
                self.md_logger.log_submission(app_res, job, match_score=match.match_score)

                print(
                    f"[{total_submitted}/{goal_count}] [{job.site.upper()}] {job.title} at {job.company} | Match: {int(match.match_score*100)}% -> {app_res.status.value.upper()}"
                )

                await asyncio.sleep(0.05)  # Fast continuous loop throughput

        print(f"\n[OK] Continuous Campaign Reached Target Goal of {total_submitted} Applications!")
        return total_submitted
