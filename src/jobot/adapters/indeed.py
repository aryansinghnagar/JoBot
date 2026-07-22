import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobot.adapters.base import SiteAdapter
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class IndeedAdapter(SiteAdapter):
    """
    Indeed Portal Adapter.
    """

    def __init__(self) -> None:
        super().__init__("indeed")

    async def _jitter_delay(self) -> None:
        await asyncio.sleep(random.uniform(1.5, 3.5))

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        await self._jitter_delay()
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        await self._jitter_delay()
        return JobPosting(
            job_id=str(uuid.uuid4()),
            site="indeed",
            url=url,
            title="Senior Python Developer",
            company="Indeed Employer",
            location="Remote / India",
            description="Looking for Python, SQL, REST APIs.",
            parsed_skills=["Python", "SQL", "REST API"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        await self._jitter_delay()
        filled_data = {
            "applicant_name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}",
            "applicant_email": profile.personal_info.email,
            "phone_number": profile.personal_info.phone,
            "resume_attached": True,
        }
        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        return filled_data

    async def submit_application(self, application: Application) -> bool:
        await self._jitter_delay()
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        await self._jitter_delay()
        application.status = ApplicationStatus.VERIFIED
        return True
