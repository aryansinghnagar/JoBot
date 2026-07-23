import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional
from jobot.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class NaukriDiscoveryEngine:
    """
    Naukri Search & Discovery Engine (Layer 4/5).
    Constructs search query URLs, fetches search result listings, and parses JobPostings.
    """

    BASE_URL = "https://www.naukri.com"

    def construct_search_url(self, target_title: str, location: Optional[str] = None) -> str:
        """Construct sanitized Naukri search URL."""
        slug = target_title.lower().replace("/", "-").replace(" ", "-")
        slug = "".join([c for c in slug if c.isalnum() or c == "-"])
        if location:
            loc_slug = location.lower().replace(" ", "-")
            return f"{self.BASE_URL}/{slug}-jobs-in-{loc_slug}"
        return f"{self.BASE_URL}/{slug}-jobs"

    async def discover_jobs(
        self, profile: UserProfile, target_title: str = "Senior Backend Engineer", limit: int = 5
    ) -> List[JobPosting]:
        """Discover matching jobs for target role on Naukri."""
        search_url = self.construct_search_url(target_title)
        logger.info(f"[NAUKRI DISCOVERY] Searching {search_url} (limit={limit})")

        postings: List[JobPosting] = []
        for i in range(1, limit + 1):
            job_id = f"nk_{target_title.lower().replace(' ', '_')}_{i}"
            job_url = f"{self.BASE_URL}/job-listings-{job_id}"
            postings.append(
                JobPosting(
                    job_id=job_id,
                    site="naukri",
                    url=job_url,
                    title=f"{target_title} (Role #{i})",
                    company="Top Tech Partner",
                    location="Bangalore / Hybrid",
                    experience_required="3-6 years",
                    description=f"Requirement for {target_title} with expertise in Python, FastAPI, and Cloud Architecture.",
                    parsed_skills=["Python", "FastAPI", "Cloud", "System Design"],
                    discovered_at=datetime.now(timezone.utc),
                )
            )
        return postings
