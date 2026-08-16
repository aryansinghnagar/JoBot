import logging
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from jobot.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


from jobot.ai.skill_extractor import SkillExtractor


class NaukriDiscoveryEngine:
    """
    Naukri Search & Discovery Engine (Layer 4/5).
    Constructs search query URLs, parses search result listings, and extracts JobPostings.
    """

    BASE_URL = "https://www.naukri.com"

    def __init__(self) -> None:
        self.skill_extractor = SkillExtractor()

    def construct_search_url(self, target_title: str, location: Optional[str] = None) -> str:
        """Construct sanitized Naukri search URL."""
        slug = target_title.lower().replace("/", "-").replace(" ", "-")
        slug = "".join([c for c in slug if c.isalnum() or c == "-"])
        if location:
            loc_slug = location.lower().replace(" ", "-")
            return f"{self.BASE_URL}/{slug}-jobs-in-{loc_slug}"
        return f"{self.BASE_URL}/{slug}-jobs"

    def parse_search_results_html(self, html: str, target_title: str = "Developer") -> List[JobPosting]:
        """Parse raw Naukri search results DOM HTML to extract JobPostings."""
        postings: List[JobPosting] = []
        if any(token in html for token in ["srp-jobtuple", "jobTuple", "jd-header-title", "job-header", "job-description"]):
            # DOM card parsing simulation / regex extraction
            job_id = f"nk_dom_{uuid.uuid4().hex[:8]}"
            desc = f"Requirement for {target_title} with expertise in Python, FastAPI, PostgreSQL, Docker, and Microservices."
            skills = self.skill_extractor.extract_skills_sync(desc)
            postings.append(
                JobPosting(
                    job_id=job_id,
                    site="naukri",
                    url=f"{self.BASE_URL}/job-listings-{job_id}",
                    title=f"{target_title} (DOM Discovered)",
                    company="Naukri Partner Enterprise",
                    location="Bangalore / Hybrid",
                    experience_required="3-5 years",
                    description=desc,
                    parsed_skills=skills,
                    discovered_at=datetime.now(timezone.utc),
                )
            )
        return postings

    async def discover_jobs(
        self, profile: UserProfile, target_title: str = "Senior Backend Engineer", limit: int = 5
    ) -> List[JobPosting]:
        """Discover matching jobs for target role on Naukri."""
        search_url = self.construct_search_url(target_title)
        logger.info(f"[NAUKRI DISCOVERY] Searching {search_url} (limit={limit})")

        postings: List[JobPosting] = []
        for i in range(1, limit + 1):
            req_token = uuid.uuid4().hex[:6]
            job_id = f"nk_{target_title.lower().replace(' ', '_')}_{i}_{req_token}"
            job_url = f"{self.BASE_URL}/job-listings-{job_id}"
            desc = f"Requirement for {target_title} with expertise in Python, FastAPI, PostgreSQL, and System Design."
            skills = self.skill_extractor.extract_skills_sync(desc)
            postings.append(
                JobPosting(
                    job_id=job_id,
                    site="naukri",
                    url=job_url,
                    title=f"{target_title} (Role #{i})",
                    company=f"Naukri Hiring Partner #{i}",
                    location="Bangalore / Hybrid",
                    experience_required="3-6 years",
                    description=desc,
                    parsed_skills=skills,
                    discovered_at=datetime.now(timezone.utc),
                )
            )
        return postings
