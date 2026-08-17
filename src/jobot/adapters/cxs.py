"""Candidate Experience API (CXS) & ATS Adapter Family — DISCOVERY ONLY.

These adapters can extract minimal job metadata from URLs on Ashby, Workable,
Recruitee, Teamtailor, and BambooHR.  They do NOT have real submission or
verification capabilities — calling submit or verify will raise
``AdapterCapabilityError``.

Real job discovery for these platforms is handled by the scraper layer
(``jobot.scrapers.ats``) which hits their public JSON APIs.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability, AdapterCapabilityError
from jobot.models.domain import (
    Application,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.security.url_guard import validate_fetch_url

logger = logging.getLogger(__name__)


class AshbyAdapter(SiteAdapter):
    """Ashby adapter — discovery and URL parsing only."""

    capabilities = AdapterCapability.DISCOVERY_PARSE

    def __init__(self, site_name: str = "ashby") -> None:
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True  # Public API requires no pre-login

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        match = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([a-f0-9-]+)", url)
        job_id = match.group(2) if match else url.rstrip("/").split("/")[-1]
        company = match.group(1).capitalize() if match else "Ashby Employer"

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Position at {company}",
            company=company,
            location="Remote / Hybrid",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Use 'jobot scrape ashby' for job discovery only.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "Ashby submission is not implemented — no confirmation to verify.",
        )


class WorkableAdapter(SiteAdapter):
    """Workable adapter — discovery and URL parsing only."""

    capabilities = AdapterCapability.DISCOVERY_PARSE

    def __init__(self, site_name: str = "workable") -> None:
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        match = re.search(r"apply\.workable\.com/([^/]+)/j/([^/]+)", url)
        company = match.group(1).capitalize() if match else "Workable Employer"
        job_id = match.group(2) if match else url.rstrip("/").split("/")[-1]

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Position at {company}",
            company=company,
            location="Flexible",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Use 'jobot scrape workable' for job discovery only.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "Workable submission is not implemented — no confirmation to verify.",
        )


class RecruiteeAdapter(SiteAdapter):
    """Recruitee adapter — discovery and URL parsing only."""

    capabilities = AdapterCapability.DISCOVERY_PARSE

    def __init__(self, site_name: str = "recruitee") -> None:
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        company = "Recruitee Partner"
        match = re.search(r"([^.]+)\.recruitee\.com", url)
        if match:
            company = match.group(1).capitalize()
        job_id = url.rstrip("/").split("/")[-1]

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Position at {company}",
            company=company,
            location="Hybrid",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Use 'jobot scrape recruitee' for job discovery only.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "Recruitee submission is not implemented — no confirmation to verify.",
        )


class TeamtailorAdapter(SiteAdapter):
    """Teamtailor adapter — discovery and URL parsing only."""

    capabilities = AdapterCapability.DISCOVERY_PARSE

    def __init__(self, site_name: str = "teamtailor") -> None:
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        company = "Teamtailor Partner"
        job_id = url.rstrip("/").split("/")[-1]

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Position at {company}",
            company=company,
            location="Remote",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Use 'jobot scrape teamtailor' for job discovery only.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "Teamtailor submission is not implemented — no confirmation to verify.",
        )


class BambooHRAdapter(SiteAdapter):
    """BambooHR adapter — discovery and URL parsing only."""

    capabilities = AdapterCapability.DISCOVERY_PARSE

    def __init__(self, site_name: str = "bamboohr") -> None:
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        company = "BambooHR Client"
        match = re.search(r"([^.]+)\.bamboohr\.com", url)
        if match:
            company = match.group(1).capitalize()
        job_id = url.rstrip("/").split("/")[-1]

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Position at {company}",
            company=company,
            location="India / Remote",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        raise AdapterCapabilityError(self.site_name, "fill_form")

    async def submit_application(self, application: Application) -> bool:
        raise AdapterCapabilityError(
            self.site_name,
            "submit_application",
            "Use 'jobot scrape bamboohr' for job discovery only.",
        )

    async def verify_submission(self, application: Application) -> VerificationResult:
        raise AdapterCapabilityError(
            self.site_name,
            "verify_submission",
            "BambooHR submission is not implemented — no confirmation to verify.",
        )


__all__ = [
    "AshbyAdapter",
    "BambooHRAdapter",
    "RecruiteeAdapter",
    "TeamtailorAdapter",
    "WorkableAdapter",
]
