import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobaut.adapters.base import SiteAdapter
from jobaut.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class MockATSAdapter(SiteAdapter):
    """
    Adapter for local Mock ATS Server used in automated closed-loop architecture testing.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        super().__init__("mock_ats")
        self.base_url = base_url

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        return JobPosting(
            job_id=str(uuid.uuid4()),
            site="mock_ats",
            url=url,
            title="Senior Software Engineer (Test)",
            company="Acme Testing Corp",
            location="Bangalore, India",
            description="Looking for Python, FastAPI, and Pydantic expertise.",
            parsed_skills=["Python", "FastAPI", "Pydantic"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        filled_fields = {
            "first_name": profile.personal_info.first_name or "TestCandidate",
            "last_name": profile.personal_info.last_name or "User",
            "email": profile.personal_info.email or "test@example.com",
            "phone": profile.personal_info.phone or "+919876543210",
            "notice_period": f"{profile.compensation.notice_period_days} Days",
            "expected_ctc": f"{profile.compensation.expected_ctc_inr or 1800000} INR",
        }
        application.form_values = filled_fields
        application.status = ApplicationStatus.FILLED
        return filled_fields

    async def submit_application(self, application: Application) -> bool:
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        application.status = ApplicationStatus.VERIFIED
        return True
