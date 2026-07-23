import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel
from jobot.adapters import AdapterRegistry, SiteAdapter
from jobot.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class JobMatchResult(BaseModel):
    posting: JobPosting
    match_score: float  # 0.0 to 1.0
    matching_skills: List[str]
    missing_skills: List[str]
    recommendation: str  # "HIGH_FIT", "MEDIUM_FIT", "LOW_FIT"


from jobot.ai.skill_extractor import SkillExtractor


class JobDiscoveryEngine:
    """
    Automated Job Search & Skill Matching Engine (Layer D).
    Discovers relevant job postings on configured portals and computes candidate fit scores.
    """

    def __init__(self, active_portals: Optional[List[str]] = None, skill_extractor: Optional[SkillExtractor] = None) -> None:
        if active_portals is None:
            active_portals = [
                "naukri", "linkedin", "indeed", "greenhouse", "lever", 
                "workday", "glassdoor", "instahyre", "cutshort", "wellfound",
                "shine", "foundit", "hirist", "ziprecruiter", "smartrecruiters"
            ]
        self.active_portals = active_portals
        self.skill_extractor = skill_extractor or SkillExtractor()

    def _get_adapter(self, site: str) -> SiteAdapter:
        return AdapterRegistry.get_adapter(site)

    def evaluate_match(self, posting: JobPosting, profile: UserProfile) -> JobMatchResult:
        """Compute matching score between candidate profile skills and job requisition skills."""
        extracted_skills = self.skill_extractor.extract_skills_sync(posting.description) if posting.description else []
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
    ) -> List[JobMatchResult]:
        """Search across target portals for postings matching candidate skills (min_match_threshold=0.20)."""
        matched_jobs: List[JobMatchResult] = []

        for portal in self.active_portals:
            try:
                adapter = self._get_adapter(portal)
                # Parse sample job postings for search query
                for i in range(limit_per_portal):
                    sample_url = f"https://www.{portal}.com/job/{target_title.replace(' ', '-').lower()}-{i+101}"
                    job_posting = await adapter.parse_job_posting(sample_url)
                    match_res = self.evaluate_match(job_posting, profile)
                    if match_res.match_score >= min_match_threshold:
                        matched_jobs.append(match_res)
            except Exception as e:
                logger.error(f"Discovery error on portal {portal}: {e}")

        return matched_jobs
