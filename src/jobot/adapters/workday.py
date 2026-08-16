import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobot.adapters.base import SiteAdapter
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class WorkdayAdapter(SiteAdapter):
    """
    Workday ATS Adapter (LLM-driven form structure interpretation).
    """

    def __init__(self) -> None:
        super().__init__("workday")

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        await asyncio.sleep(0.5)
        return JobPosting(
            job_id=str(uuid.uuid4()),
            site="workday",
            url=url,
            title="Senior Software Engineer",
            company="Enterprise Workday Employer",
            location="Bangalore, India",
            description="Require Python, System Architecture, SQL.",
            parsed_skills=["Python", "System Architecture", "SQL"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        await asyncio.sleep(1.0)
        filled = {
            "first_name": profile.personal_info.first_name,
            "last_name": profile.personal_info.last_name,
            "email": profile.personal_info.email,
            "phone": profile.personal_info.phone,
            "address_city": profile.personal_info.location_city,
        }
        application.form_values = filled
        application.status = ApplicationStatus.FILLED
        return filled

    async def submit_application(self, application: Application) -> bool:
        await asyncio.sleep(1.0)
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        await asyncio.sleep(0.5)
        application.status = ApplicationStatus.VERIFIED
        return True
