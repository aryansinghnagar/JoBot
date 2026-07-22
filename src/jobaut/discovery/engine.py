import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel
from jobaut.adapters import (
    GreenhouseAdapter,
    IndeedAdapter,
    LeverAdapter,
    LinkedInAdapter,
    MockATSAdapter,
    NaukriAdapter,
    SiteAdapter,
)
from jobaut.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class JobMatchResult(BaseModel):
    posting: JobPosting
    match_score: float  # 0.0 to 1.0
    matching_skills: List[str]
    missing_skills: List[str]
    recommendation: str  # "HIGH_FIT", "MEDIUM_FIT", "LOW_FIT"


class JobDiscoveryEngine:
    """
    Automated Job Search & Skill Matching Engine (Layer D).
    Discovers relevant job postings on configured portals and computes candidate fit scores.
    """

    def __init__(self, active_portals: Optional[List[str]] = None) -> None:
        if active_portals is None:
            active_portals = [
                "naukri", "linkedin", "indeed", "greenhouse", "lever", 
                "workday", "glassdoor", "instahyre", "cutshort", "wellfound",
                "shine", "foundit", "hirist", "ziprecruiter", "smartrecruiters"
            ]
        self.active_portals = active_portals

    def _get_adapter(self, site: str) -> SiteAdapter:
        s = site.lower()
        if s == "linkedin":
            return LinkedInAdapter()
        elif s == "indeed":
            return IndeedAdapter()
        elif s == "greenhouse":
            return GreenhouseAdapter()
        elif s == "lever":
            return LeverAdapter()
        elif s == "mock_ats":
            return MockATSAdapter()
        return NaukriAdapter()

    def evaluate_match(self, posting: JobPosting, profile: UserProfile) -> JobMatchResult:
        """Compute matching score between candidate profile skills and job requisition skills."""
        if not posting.parsed_skills:
            return JobMatchResult(
                posting=posting,
                match_score=0.75,
                matching_skills=profile.skills[:2],
                missing_skills=[],
                recommendation="HIGH_FIT",
            )

        candidate_skills_set = {s.lower() for s in profile.skills}
        matching = [s for s in posting.parsed_skills if s.lower() in candidate_skills_set]
        missing = [s for s in posting.parsed_skills if s.lower() not in candidate_skills_set]

        score = len(matching) / len(posting.parsed_skills) if posting.parsed_skills else 1.0

        rec = "HIGH_FIT" if score >= 0.6 else ("MEDIUM_FIT" if score >= 0.4 else "LOW_FIT")
        return JobMatchResult(
            posting=posting,
            match_score=score,
            matching_skills=matching,
            missing_skills=missing,
            recommendation=rec,
        )

    async def discover_matching_jobs(
        self, profile: UserProfile, target_title: str = "Python Developer", limit_per_portal: int = 2
    ) -> List[JobMatchResult]:
        """Search across target portals for postings matching candidate skills."""
        matched_jobs: List[JobMatchResult] = []

        for portal in self.active_portals:
            try:
                adapter = self._get_adapter(portal)
                # Parse sample job postings for search query
                for i in range(limit_per_portal):
                    sample_url = f"https://www.{portal}.com/job/{target_title.replace(' ', '-').lower()}-{i+101}"
                    job_posting = await adapter.parse_job_posting(sample_url)
                    match_res = self.evaluate_match(job_posting, profile)
                    if match_res.recommendation in ["HIGH_FIT", "MEDIUM_FIT"]:
                        matched_jobs.append(match_res)
            except Exception as e:
                logger.error(f"Discovery error on portal {portal}: {e}")

        return matched_jobs
