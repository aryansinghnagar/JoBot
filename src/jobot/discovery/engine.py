import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.ai.skill_extractor import SkillExtractor
from jobot.config.manager import ConfigManager
from jobot.models.domain import JobPosting, UserProfile
from jobot.scrapers.ats import FAMILY_ADAPTERS, AtsFamilyAdapter
from jobot.scrapers.careers import CareerPageScanner
from jobot.scrapers.dedup import DedupService
from jobot.scrapers.jobspy import JOBS_BOARDS, JobSpyAdapter
from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

# Boards without a real public feed: discovery skips them (no fabricated data).
UNSCRAPABLE_BOARDS = (
    "workday",
    "instahyre",
    "cutshort",
    "wellfound",
    "shine",
    "foundit",
    "hirist",
    "ziprecruiter",
    "naukri",
    "glassdoor",
)


class JobMatchResult(BaseModel):
    posting: JobPosting
    match_score: float  # 0.0 to 1.0
    matching_skills: List[str]
    missing_skills: List[str]
    recommendation: str  # "HIGH_FIT", "MEDIUM_FIT", "LOW_FIT"


class JobDiscoveryEngine:
    """
    Job discovery & skill matching (Layer D).

    Phase 2: discovery only runs against real feeds — JobSpy boards, direct-API
    ATS families, the CareerPageScanner, and the local mock ATS. Portals
    without a real feed are skipped with a warning. Never fabricates postings.
    """

    def __init__(
        self,
        active_portals: Optional[List[str]] = None,
        skill_extractor: Optional[SkillExtractor] = None,
        db: Optional[DatabaseManager] = None,
        dedup: Optional[DedupService] = None,
        config: Optional[ConfigManager] = None,
    ) -> None:
        if active_portals is None:
            active_portals = [
                "linkedin",
                "indeed",
                "glassdoor",
                "zip_recruiter",
                "google",
                "bayt",
                "bdjobs",
                "naukri",
                "lever",
                "ashby",
                "smartrecruiters",
                "greenhouse",
                "careers",
                "mock_ats",
            ]
        self.active_portals = [p for p in active_portals if p not in UNSCRAPABLE_BOARDS]
        skipped = [p for p in active_portals if p in UNSCRAPABLE_BOARDS]
        if skipped:
            logger.info("Discovery: skipping portals without a real feed: %s", skipped)
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.db = db or DatabaseManager()
        self.dedup = dedup or DedupService(db=self.db)
        self.config = config or ConfigManager()

    def _scraper_for(self, portal: str, companies: List[str]) -> Any:
        if portal in JOBS_BOARDS:
            delay = float(self.config.get("scraper.jobspy.delay_s", 1.0))
            proxies_raw = self.config.get("scraper.jobspy.proxy_list", "")
            proxies = [p.strip() for p in str(proxies_raw).split(",") if p.strip()]
            return JobSpyAdapter(portal, delay_s=delay, proxies=proxies or None)
        if portal in FAMILY_ADAPTERS:
            adapter_cls = FAMILY_ADAPTERS[portal]
            if not companies:
                logger.info("Discovery: portal '%s' needs --companies; skipping", portal)
                return None
            return adapter_cls(company=companies[0])
        if portal == "greenhouse":
            from jobot.adapters.greenhouse import GreenhouseAdapter

            if not companies:
                logger.info("Discovery: portal 'greenhouse' needs --companies; skipping")
                return None
            return GreenhouseAdapter()
        if portal == "careers":
            return CareerPageScanner(companies=companies)
        if portal == "mock_ats":
            return MockATSAdapter()
        logger.warning("Discovery: no scraper for portal '%s'; skipping", portal)
        return None

    def scraper_for(self, portal: str, companies: List[str]) -> Any:
        """Public scraper resolution for a portal (used by the GUI sidecar)."""
        return self._scraper_for(portal, companies)

    def evaluate_match(self, posting: JobPosting, profile: UserProfile) -> JobMatchResult:
        """Compute matching score between candidate profile skills and job requisition skills."""
        extracted_skills = (
            self.skill_extractor.extract_skills_sync(posting.description)
            if posting.description
            else []
        )
        combined_skills = list(dict.fromkeys(posting.parsed_skills + extracted_skills))
        skills_to_check = combined_skills if combined_skills else posting.parsed_skills

        if not skills_to_check:
            return JobMatchResult(
                posting=posting,
                match_score=0.75,
                matching_skills=profile.skills[:2],
                missing_skills=[],
                recommendation="HIGH_FIT",
            )

        candidate_skills_set = {s.lower() for s in profile.skills}
        matching = [s for s in skills_to_check if s.lower() in candidate_skills_set]
        missing = [s for s in skills_to_check if s.lower() not in candidate_skills_set]

        score = len(matching) / len(skills_to_check) if skills_to_check else 1.0

        rec = "HIGH_FIT" if score >= 0.6 else ("MEDIUM_FIT" if score >= 0.4 else "LOW_FIT")
        return JobMatchResult(
            posting=posting,
            match_score=score,
            matching_skills=matching,
            missing_skills=missing,
            recommendation=rec,
        )

    async def discover_matching_jobs(
        self,
        profile: UserProfile,
        target_title: str = "Python Developer",
        limit_per_portal: int = 2,
        min_match_threshold: float = 0.20,
        companies: Optional[List[str]] = None,
        location: str = "",
    ) -> List[JobMatchResult]:
        """Search real feeds for postings matching the candidate profile (dedup applied)."""
        companies = companies or []
        matched_jobs: List[JobMatchResult] = []

        for portal in self.active_portals:
            try:
                scraper = self._scraper_for(portal, companies)
                if scraper is None:
                    continue
                postings = await scraper.discover_jobs(
                    keywords=target_title, location=location, limit=limit_per_portal
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Discovery error on portal %s: %s", portal, exc)
                continue

            unique = self.dedup.filter_unique(postings).unique
            for posting in unique:
                match_res = self.evaluate_match(posting, profile)
                if match_res.match_score >= min_match_threshold:
                    matched_jobs.append(match_res)

        matched_jobs.sort(key=lambda r: r.match_score, reverse=True)
        return matched_jobs
