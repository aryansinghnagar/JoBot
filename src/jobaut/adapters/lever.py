import asyncio
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobaut.adapters.base import SiteAdapter
from jobaut.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class LeverAdapter(SiteAdapter):
    """
    Lever ATS Adapter.
    """

    def __init__(self) -> None:
        super().__init__("lever")

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        await asyncio.sleep(0.5)
        return JobPosting(
            job_id=str(uuid.uuid4()),
            site="lever",
            url=url,
            title="Full Stack Engineer",
            company="Lever Customer Org",
            location="Bangalore, India",
            description="Require Python, FastAPI, React.",
            parsed_skills=["Python", "FastAPI", "React"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        await asyncio.sleep(0.8)
        filled_data = {
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}",
            "email": profile.personal_info.email,
            "phone": profile.personal_info.phone,
            "org": "Current Employer",
            "urls": {"LinkedIn": profile.personal_info.linkedin_url or ""},
        }
        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        return filled_data

    async def submit_application(self, application: Application) -> bool:
        await asyncio.sleep(1.0)
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        await asyncio.sleep(0.5)
        application.status = ApplicationStatus.VERIFIED
        return True
