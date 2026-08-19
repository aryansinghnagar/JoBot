from abc import ABC, abstractmethod
from typing import Any

from jobot.adapters.capabilities import AdapterCapability
from jobot.models.domain import Application, JobPosting, UserProfile, VerificationResult


class SiteAdapter(ABC):
    """
    Abstract Base Class for Portal & ATS Adapters (Layer F).
    Each adapter encapsulates login, posting parsing, form filling, submission, and verification.

    Subclasses MUST set ``capabilities`` to accurately reflect what the adapter
    can actually do.  The default is ``FULL_API`` for backward compatibility
    with real HTTP-based adapters (Greenhouse, Lever).  Discovery-only adapters
    MUST override this to ``AdapterCapability.DISCOVERY_ONLY``.
    """

    capabilities: AdapterCapability = AdapterCapability.FULL_API

    def __init__(self, site_name: str):
        self.site_name = site_name

    @abstractmethod
    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        """Authenticate with the site using existing session or vault credentials."""
        pass

    @abstractmethod
    async def parse_job_posting(self, url: str) -> JobPosting:
        """Parse job details, required skills, and qualifications from a job posting URL."""
        pass

    @abstractmethod
    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> dict[str, Any]:
        """Map profile facts to form fields and perform non-submitting form fill."""
        pass

    @abstractmethod
    async def submit_application(self, application: Application) -> bool:
        """Execute submission action (supervised or autonomous based on trust level)."""

    @abstractmethod
    async def verify_submission(self, application: Application) -> VerificationResult:
        """Verify that application was successfully received by external site/ATS."""
        pass

    async def extract_form_questions(self, job: JobPosting) -> list[str]:
        """Extract interactive form questions from job posting page."""
        return [
            "What is your full name?",
            "What is your email address?",
            "What is your notice period?",
        ]

    async def capture_screenshot(self) -> bytes | None:
        """Capture screenshot of current page state for evidence recording."""
        return None
