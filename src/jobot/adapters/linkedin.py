"""LinkedIn Adapter — honest discovery + live Easy Apply saga wiring (Phase 3 T3.5, Phase 5 T4.2).

Fabrication removed: this adapter never invents postings, form values, or
confirmation IDs. Discovery of real postings happens through the jobspy
scraper (`jobot scrape linkedin`). Application actions run the Easy Apply
saga (T3.6) through a real Patchright browser session and are refused
honestly when live browser runs are disabled (JOBOT_RUN_LIVE_BROWSER=1).
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.stealth.browser import BrowserSession
from jobot.stealth.linkedin_easy_apply import EasyApplySaga
from jobot.storage.vault import CredentialVault

logger = logging.getLogger(__name__)


class LinkedInAdapter(SiteAdapter):
    """
    LinkedIn Adapter. Discovery is honest (jobspy scraper). With live browser
    runs enabled, submit/verify drive the Easy Apply saga; otherwise they
    raise explicit errors instead of fabricating results.
    """

    def __init__(
        self,
        vault: Optional[CredentialVault] = None,
        saga_factory: Optional[Callable[[BrowserSession], EasyApplySaga]] = None,
        profile_loader: Optional[Callable[[], UserProfile]] = None,
        browser_provider: Optional[Callable[[], Any]] = None,
    ) -> None:
        super().__init__("linkedin")
        self._vault = vault or CredentialVault()
        self._saga_factory = saga_factory or (lambda browser: EasyApplySaga(browser))
        self._profile_loader = profile_loader or self._load_profile
        self._browser_provider = browser_provider or self._start_browser
        self._session: Optional[BrowserSession] = None

    def _live_enabled(self) -> bool:
        return os.getenv("JOBOT_RUN_LIVE_BROWSER") == "1"

    async def _start_browser(self) -> BrowserSession:
        if self._session is None:
            self._session = BrowserSession(portal="linkedin", headless=True)
            await self._session.start()
        return self._session

    async def _browser_session(self) -> BrowserSession:
        session = await self._browser_provider()
        if session is None:
            raise RuntimeError("Browser provider returned None.")
        return session

    def _load_profile(self) -> UserProfile:
        profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
        if not profile_path.exists():
            raise FileNotFoundError(
                f"Profile missing at {profile_path} — run 'jobot profile init' first."
            )
        return self._vault.load_encrypted_profile(profile_path)

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
        if not self._live_enabled():
            raise NotImplementedError(
                "LinkedIn Easy Apply form filling requires a live browser session "
                "(JOBOT_RUN_LIVE_BROWSER=1)."
            )
        info = profile.personal_info
        form: Dict[str, Any] = {
            "email": info.email,
            "name": f"{info.first_name} {info.last_name}".strip(),
        }
        if info.first_name:
            form["first_name"] = info.first_name
        if info.last_name:
            form["last_name"] = info.last_name
        if info.phone:
            form["phone"] = info.phone
        return form

    async def submit_application(self, application: Application) -> bool:
        if not self._live_enabled():
            raise NotImplementedError(
                "LinkedIn Easy Apply submission requires a live browser session "
                "(JOBOT_RUN_LIVE_BROWSER=1) running the Easy Apply saga."
            )
        if not application.job_url:
            logger.warning("[LINKEDIN] No job_url on application — cannot run Easy Apply.")
            return False
        profile = self._profile_loader()
        browser = await self._browser_session()
        saga = self._saga_factory(browser)
        result = await saga.run(application.job_url, profile)
        if not result.success:
            logger.warning(f"[LINKEDIN] Easy Apply failed: {result.reason}")
            return False
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> VerificationResult:
        if not self._live_enabled():
            raise NotImplementedError(
                "LinkedIn Easy Apply verification requires a live browser session "
                "(JOBOT_RUN_LIVE_BROWSER=1) running the Easy Apply saga."
            )
        if not application.job_url:
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason="No job_url on application — cannot verify.",
            )
        browser = await self._browser_session()
        saga = self._saga_factory(browser)
        result = await saga.verify_submitted(application.job_url)
        if result.success:
            application.status = ApplicationStatus.VERIFIED
            return VerificationResult(
                success=True,
                confidence=0.85,
                confirmation_id=application.job_id,
                evidence_snapshot_path=result.evidence_shots[0] if result.evidence_shots else None,
                reason=result.reason,
            )
        return VerificationResult(
            success=False,
            confidence=0.0,
            reason=result.reason,
        )
