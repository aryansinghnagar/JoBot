import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.adapters.naukri.discovery import NaukriDiscoveryEngine
from jobot.adapters.naukri.form_fill import NaukriFormFiller
from jobot.adapters.naukri.login import NaukriLoginFlow
from jobot.adapters.naukri.submit import NaukriSubmitter
from jobot.adapters.naukri.verify import NaukriVerifier
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class NaukriAdapter(SiteAdapter):
    """
    Naukri.com Portal Adapter (Primary India Market Focus).
    Integrates Patchright browser automation, login persistence, real form filling, and submission verification.
    """

    def __init__(self) -> None:
        super().__init__("naukri")
        self.login_flow = NaukriLoginFlow()
        self.discovery_engine = NaukriDiscoveryEngine()
        self.form_filler = NaukriFormFiller()
        self.submitter = NaukriSubmitter()
        self.verifier = NaukriVerifier()

    async def _jitter_delay(self, min_sec: float = 0.5, max_sec: float = 1.5) -> None:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        await self._jitter_delay(0.2, 0.8)
        return await self.login_flow.execute_login(username, password)

    async def parse_job_posting(self, url: str) -> JobPosting:
        await self._jitter_delay(0.3, 1.0)
        job_id = url.split("/")[-1] if "/" in url else str(uuid.uuid4())
        return JobPosting(
            job_id=job_id,
            site="naukri",
            url=url,
            title="Senior Backend Engineer",
            company="Naukri Hiring Partner",
            location="Bangalore / Hybrid",
            experience_required="3-6 years",
            description="Require Python, Django/FastAPI, PostgreSQL expertise.",
            parsed_skills=["Python", "FastAPI", "PostgreSQL", "System Design"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        await self._jitter_delay(0.5, 1.5)
        return await self.form_filler.fill_application_form(job, profile, application)

    async def submit_application(self, application: Application) -> bool:
        await self._jitter_delay(0.5, 1.5)
        return await self.submitter.submit(application)

    async def verify_submission(self, application: Application) -> bool:
        await self._jitter_delay(0.2, 0.8)
        return await self.verifier.verify(application)
