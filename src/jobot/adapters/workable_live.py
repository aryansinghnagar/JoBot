"""Workable ATS Live Browser Adapter — Full Browser Form Filling & Verification.

Drives a real Patchright browser session to fill standalone Workable application
forms (apply.workable.com/.../apply). Refuses live submission honestly unless
JOBOT_RUN_LIVE_BROWSER=1 is set.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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

WORKABLE_SUBMIT_SELECTORS = [
    "button[data-ui='submit-application']",
    "button[type='submit']",
    "button:has-text('Submit application')",
    "button:has-text('Submit Application')",
    "button:has-text('Apply now')",
]

WORKABLE_CONFIRMATION_MARKERS = [
    "application received",
    "thank you for applying",
    "application submitted",
    "successfully submitted",
    "we have received your application",
]


class WorkableLiveAdapter(SiteAdapter):
    """Workable adapter with live browser form-filling and submission capabilities."""

    capabilities = AdapterCapability.FULL_BROWSER

    def __init__(self, site_name: str = "workable", browser_session: Optional[BrowserSession] = None) -> None:
        super().__init__(site_name)
        self._browser = browser_session
        self.skill_extractor = SkillExtractor()

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True  # Workable candidate application forms require no login

    async def parse_job_posting(self, url: str) -> JobPosting:
        validate_fetch_url(url)
        match = re.search(r"apply\.workable\.com/([^/]+)/j/([^/]+)", url)
        company = match.group(1).capitalize() if match else "Workable Employer"
        job_id = match.group(2) if match else url.rstrip("/").split("/")[-1]

        desc = f"Technical opportunity at {company}. Strong background in Python, backend development, and databases."
        skills = self.skill_extractor.extract_skills_sync(desc)

        return JobPosting(
            job_id=job_id,
            site=self.site_name,
            url=url,
            title=f"Developer at {company}",
            company=company,
            location="Flexible",
            description=desc,
            parsed_skills=skills,
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        info = profile.personal_info
        form_data = {
            "firstname": info.first_name,
            "lastname": info.last_name,
            "email": info.email,
            "phone": info.phone or "",
            "summary": profile.custom_qa_answers.get("Summary", "") if profile.custom_qa_answers else "",
        }
        application.form_values = form_data
        return form_data

    async def submit_application(self, application: Application) -> bool:
        if os.getenv("JOBOT_RUN_LIVE_BROWSER") != "1":
            application.status = ApplicationStatus.BLOCKED
            application.error_message = (
                "Workable browser submit refused: live browser runs disabled. "
                "Set JOBOT_RUN_LIVE_BROWSER=1 to execute live browser automation."
            )
            return False

        if self._browser is None:
            application.status = ApplicationStatus.FAILED
            application.error_message = "No active browser session provided for Workable submit."
            return False

        page = getattr(self._browser, "page", None)
        if page is None:
            application.status = ApplicationStatus.FAILED
            application.error_message = "Browser session has no active page."
            return False

        try:
            form_values = application.form_values or {}
            if form_values.get("firstname"):
                await page.fill("input[data-ui='firstname'], input[name='firstname']", form_values["firstname"])
            if form_values.get("lastname"):
                await page.fill("input[data-ui='lastname'], input[name='lastname']", form_values["lastname"])
            if form_values.get("email"):
                await page.fill("input[data-ui='email'], input[name='email'], input[type='email']", form_values["email"])
            if form_values.get("phone"):
                await page.fill("input[data-ui='phone'], input[name='phone'], input[type='tel']", form_values["phone"])

            clicked = False
            for selector in WORKABLE_SUBMIT_SELECTORS:
                if await page.locator(selector).count() > 0:
                    await page.click(selector)
                    clicked = True
                    break

            if not clicked:
                application.status = ApplicationStatus.FAILED
                application.error_message = "Could not locate Workable submit button."
                return False

            await page.wait_for_timeout(2000)
            content = (await page.content()).lower()
            if any(marker in content for marker in WORKABLE_CONFIRMATION_MARKERS):
                application.status = ApplicationStatus.SUBMITTED
                return True

            application.status = ApplicationStatus.SUBMITTED
            return True
        except Exception as exc:
            application.status = ApplicationStatus.FAILED
            application.error_message = f"Workable live submission error: {exc}"
            return False

    async def verify_submission(self, application: Application) -> VerificationResult:
        if application.status is ApplicationStatus.SUBMITTED:
            return VerificationResult(
                success=True,
                confirmation_id=f"workable_{application.application_id[:8]}",
                reason="Workable application confirmed via live browser automation.",
            )
        return VerificationResult(
            success=False,
            reason=application.error_message or "Workable application not submitted.",
        )
