"""LinkedIn Adapter — honest discovery-only (Phase 3, T3.5).

Fabrication removed: this adapter never invents postings, form values, or
confirmation IDs. Discovery of real postings happens through the jobspy
scraper (`jobot scrape linkedin`). Application actions require the Easy Apply
saga (T3.6) with a real browser session and raise explicit errors until then.
"""

from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.models.domain import (
    Application,
    JobPosting,
    UserProfile,
    VerificationResult,
)


class LinkedInAdapter(SiteAdapter):
    """
    LinkedIn Adapter. Discovery is honest (jobspy scraper); parse/fill/submit
    raise explicit errors until the Easy Apply browser saga is available.
    """

    def __init__(self) -> None:
        super().__init__("linkedin")

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        raise NotImplementedError(
            "LinkedIn posting parsing requires a real browser session. "
            "Discover real postings with 'jobot scrape linkedin'."
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "LinkedIn Easy Apply form filling requires a browser session. "
            "Use 'jobot login linkedin' then the Easy Apply saga."
        )

    async def submit_application(self, application: Application) -> bool:
        raise NotImplementedError(
            "LinkedIn Easy Apply submission requires a browser session (Easy Apply saga)."
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise NotImplementedError(
            "LinkedIn Easy Apply verification requires the Easy Apply saga browser session."
        )
