import asyncio
import logging
import os
import random
import uuid
from datetime import UTC, datetime
from typing import Any

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability
from jobot.adapters.naukri.discovery import NaukriDiscoveryEngine
from jobot.adapters.naukri.form_fill import NaukriFormFiller
from jobot.adapters.naukri.login import NaukriLoginFlow
from jobot.adapters.naukri.submit import NaukriSubmitter
from jobot.adapters.naukri.verify import NaukriVerifier
from jobot.models.domain import Application, JobPosting, UserProfile, VerificationResult
from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)


class NaukriAdapter(SiteAdapter):
    """
    Naukri.com Portal Adapter (Primary India Market Focus).
    Integrates Patchright browser automation, login persistence, real form filling, and submission verification.

    P1.1/P1.2: submit and verify drive a real browser page and refuse to
    fabricate results. Live browser runs are opt-in via JOBOT_RUN_LIVE_BROWSER=1.
    """

    capabilities = AdapterCapability.FULL_BROWSER

    def __init__(self) -> None:
        super().__init__("naukri")
        self.login_flow = NaukriLoginFlow()
        self.discovery_engine = NaukriDiscoveryEngine()
        self.form_filler = NaukriFormFiller()
        self.submitter = NaukriSubmitter()
        self.verifier = NaukriVerifier()
        self._session: BrowserSession | None = None

    async def _browser_page(self) -> Any | None:
        """Return an authenticated browser page when live browser runs are enabled."""
        if os.getenv("JOBOT_RUN_LIVE_BROWSER") != "1":
            logger.warning(
                "[NAUKRI] Live browser disabled (JOBOT_RUN_LIVE_BROWSER=1 to enable) — "
                "refusing to fabricate submit/verify."
            )
            return None
        if self._session is None:
            self._session = BrowserSession(portal="naukri", headless=True)
            await self._session.start()
        return await self._session.new_page()

    async def _jitter_delay(self, min_sec: float = 0.5, max_sec: float = 1.5) -> None:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        await self._jitter_delay(0.2, 0.8)
        return await self.login_flow.execute_login(username, password)

    async def parse_job_posting(self, url: str) -> JobPosting:
        await self._jitter_delay(0.3, 1.0)
        job_id = url.split("/")[-1] if "/" in url else str(uuid.uuid4())
        return JobPosting(
            job_id=job_id,
            site="naukri",
            url=url,
            title="Naukri Job Opportunity",
            company="Naukri Hiring Partner",
            location="Remote / Hybrid",
            experience_required="",
            description="",
            parsed_skills=[],
            discovered_at=datetime.now(UTC),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> dict[str, Any]:
        await self._jitter_delay(0.5, 1.5)
        return await self.form_filler.fill_application_form(job, profile, application)

    async def submit_application(self, application: Application) -> bool:
        await self._jitter_delay(0.5, 1.5)
        page = await self._browser_page()
        return await self.submitter.submit(application, page=page)

    async def verify_submission(self, application: Application) -> VerificationResult:
        await self._jitter_delay(0.2, 0.8)
        page = await self._browser_page()
        return await self.verifier.verify(application, page=page)
