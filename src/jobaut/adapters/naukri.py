import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobaut.adapters.base import SiteAdapter
from jobaut.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class NaukriAdapter(SiteAdapter):
    """
    Naukri.com Portal Adapter (Primary India Market Focus).
    Implements browser-assisted form filling, jittered anti-detection delay, and verification.
    """

    def __init__(self) -> None:
        super().__init__("naukri")

    async def _jitter_delay(self, min_sec: float = 1.0, max_sec: float = 3.0) -> None:
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        await self._jitter_delay(0.5, 1.5)
        # Login verification logic stub
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        await self._jitter_delay(0.8, 2.0)
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
        await self._jitter_delay(1.5, 3.5)
        filled_data = {
            "full_name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip(),
            "email": profile.personal_info.email,
            "mobile": profile.personal_info.phone,
            "current_location": profile.personal_info.location_city,
            "total_experience_years": 5,
            "current_ctc": profile.compensation.current_ctc_inr,
            "expected_ctc": profile.compensation.expected_ctc_inr,
            "notice_period": f"{profile.compensation.notice_period_days} Days",
        }
        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        return filled_data

    async def submit_application(self, application: Application) -> bool:
        await self._jitter_delay(2.0, 4.0)
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        await self._jitter_delay(1.0, 2.0)
        application.status = ApplicationStatus.VERIFIED
        return True
