"""Indeed Portal Adapter — DISCOVERY ONLY.

Real job discovery for Indeed is handled by the scraper layer
(``jobot.scrapers.jobspy``).  This adapter has no real submission
or verification capability.
"""

from typing import Any

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability, AdapterCapabilityError
from jobot.models.domain import (
    Application,
    JobPosting,
    UserProfile,
    VerificationResult,
)


class IndeedAdapter(SiteAdapter):
    """Indeed adapter — discovery only, no submission capability."""

    capabilities = AdapterCapability.DISCOVERY_ONLY

    def __init__(self) -> None:
        super().__init__("indeed")

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        raise AdapterCapabilityError(
            self.site_name,
            "parse_job_posting",
            "Use 'jobot scrape indeed' for real job discovery.",
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Indeed submission is not implemented.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "Indeed verification is not implemented — no confirmation to verify.",
        )
