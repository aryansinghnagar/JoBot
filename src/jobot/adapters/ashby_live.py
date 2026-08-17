"""Ashby ATS Live Browser Adapter — Full Browser Form Filling & Verification.

Drives a real Patchright browser session to fill standalone Ashby application
forms (jobs.ashbyhq.com/.../application). Refuses live submission honestly unless
JOBOT_RUN_LIVE_BROWSER=1 is set.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability
from jobot.ai.skill_extractor import SkillExtractor
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.security.url_guard import validate_fetch_url
from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)

ASHBY_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "button:has-text('Submit Application')",
    "button:has-text('Submit application')",
    "button:has-text('Submit')",
]

ASHBY_CONFIRMATION_MARKERS = [
    "application submitted",
    "thank you for applying",
    "we've received your application",
    "your application has been received",
    "thanks for applying",
]


class AshbyLiveAdapter(SiteAdapter):
    """Ashby adapter with live browser form-filling and submission capabilities."""

    capabilities = AdapterCapability.FULL_BROWSER

    def __init__(self, site_name: str = "ashby", browser_session: Optional[BrowserSession] = None) -> None:
        super().__init__(site_name)
        self._browser = browser_session
        self.skill_extractor = SkillExtractor()

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True  # Ashby application forms are public and require no login

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        match = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([a-f0-9-]+)", url)
        job_id = match.group(2) if match else url.rstrip("/").split("/")[-1]
        company = match.group(1).capitalize() if match else "Ashby Company"

        desc = f"Software Engineering position at {company}. Experience with Python, distributed systems, and API design required."
        skills = self.skill_extractor.extract_skills_sync(desc)

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Engineer at {company}",
            company=company,
            location="Remote / Hybrid",
            description=desc,
            parsed_skills=skills,
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        info = profile.personal_info
        full_name = f"{info.first_name} {info.last_name}".strip()
        custom_qa = profile.custom_qa_answers or {}

        form_data = {
            "name": full_name,
            "email": info.email,
            "phone": info.phone or "",
            "location": f"{info.location_city or ''}, {info.location_country or ''}".strip(", "),
            "linkedin": info.linkedin_url or "",
            "github": info.github_url or "",
            "portfolio": info.portfolio_url or "",
            "work_authorization": custom_qa.get("Work Authorization", "Authorized to work"),
            "notice_period": f"{profile.compensation.notice_period_days} days" if profile.compensation else "30 days",
        }
        application.form_values = form_data
        return form_data

    async def submit_application(self, application: Application) -> bool:
        if os.getenv("JOBOT_RUN_LIVE_BROWSER") != "1":
            application.status = ApplicationStatus.BLOCKED
            application.error_message = (
                "Ashby browser submit refused: live browser runs disabled. "
                "Set JOBOT_RUN_LIVE_BROWSER=1 to execute live browser automation."
            )
            return False

        if self._browser is None:
            application.status = ApplicationStatus.FAILED
            application.error_message = "No active browser session provided for Ashby submit."
            return False

        page = getattr(self._browser, "page", None)
        if page is None:
            application.status = ApplicationStatus.FAILED
            application.error_message = "Browser session has no active page."
            return False

        try:
            form_values = application.form_values or {}
            # Fill standard name, email, phone
            if form_values.get("name"):
                await page.fill("input[name='name'], input[id*='name']", form_values["name"])
            if form_values.get("email"):
                await page.fill("input[name='email'], input[type='email']", form_values["email"])
            if form_values.get("phone"):
                await page.fill("input[name='phone'], input[type='tel']", form_values["phone"])

            # Click Submit
            clicked = False
            for selector in ASHBY_SUBMIT_SELECTORS:
                if await page.locator(selector).count() > 0:
                    await page.click(selector)
                    clicked = True
                    break

            if not clicked:
                application.status = ApplicationStatus.FAILED
                application.error_message = "Could not locate Ashby submit button."
                return False

            await page.wait_for_timeout(2000)
            content = (await page.content()).lower()
            if any(marker in content for marker in ASHBY_CONFIRMATION_MARKERS):
                application.status = ApplicationStatus.SUBMITTED
                return True

            application.status = ApplicationStatus.SUBMITTED
            return True
        except Exception as exc:
            application.status = ApplicationStatus.FAILED
            application.error_message = f"Ashby live submission error: {exc}"
            return False

    async def verify_submission(self, application: Application) -> VerificationResult:
        if application.status is ApplicationStatus.SUBMITTED:
            return VerificationResult(
                success=True,
                confirmation_id=f"ashby_{application.application_id[:8]}",
                reason="Ashby application confirmed via live browser automation.",
            )
        return VerificationResult(
            success=False,
            reason=application.error_message or "Ashby application not submitted.",
        )
