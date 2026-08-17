"""Generic job-portal adapters — DISCOVERY ONLY.

These adapters exist as placeholders for platforms where JoBot has no
real submission integration.  Calling ``submit_application`` or
``verify_submission`` raises ``AdapterCapabilityError``.

Real job discovery for these platforms is handled by the scraper layer
(``jobot.scrapers.jobspy``) which uses the python-jobspy library.
"""

from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability, AdapterCapabilityError
from jobot.models.domain import (
    Application,
    JobPosting,
    UserProfile,
    VerificationResult,
)


class GenericPortalAdapter(SiteAdapter):
    """Base for portal adapters that support discovery only (no real submission)."""

    capabilities = AdapterCapability.DISCOVERY_ONLY

    def __init__(self, site_name: str):
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        raise AdapterCapabilityError(
            self.site_name,
            "parse_job_posting",
            f"Use 'jobot scrape {self.site_name}' for real job discovery.",
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            f"{self.site_name.capitalize()} submission is not implemented.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            f"{self.site_name.capitalize()} verification is not implemented "
            "— no confirmation to verify.",
        )


class GlassdoorAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("glassdoor")


class ZipRecruiterAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("ziprecruiter")


class ShineAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("shine")


class FounditAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("foundit")


class HiristAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("hirist")


class InstahyreAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("instahyre")


class CutshortAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("cutshort")


class WellfoundAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("wellfound")


class SmartRecruitersAdapter(GenericPortalAdapter):
    def __init__(self) -> None:
        super().__init__("smartrecruiters")
