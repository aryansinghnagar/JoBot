from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import urllib.error
import urllib.request
from jobot.adapters.base import SiteAdapter
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class MockATSAdapter(SiteAdapter):
    """
    Adapter for local Mock ATS Server (localhost:5800) used in automated closed-loop integration testing.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5800"):
        super().__init__("mock_ats")
        self.base_url = base_url.rstrip("/")

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        job_id = url.split("/")[-1]
        req_url = f"{self.base_url}/jobs/{job_id}"
        try:
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                return JobPosting(
                    job_id=str(data.get("id", job_id)),
                    site="mock_ats",
                    url=url,
                    title=data.get("title", "Senior Software Engineer"),
                    company=data.get("company", "Mock Corp"),
                    location=data.get("location", "Bangalore, India"),
                    description=data.get("description", ""),
                    parsed_skills=data.get("parsed_skills", []),
                    discovered_at=datetime.now(timezone.utc),
                )
        except Exception:
            return JobPosting(
                job_id=job_id,
                site="mock_ats",
                url=url,
                title="Senior Software Engineer (Offline)",
                company="Mock Corp",
                location="Bangalore, India",
                description="Fallback job description",
                parsed_skills=["Python"],
                discovered_at=datetime.now(timezone.utc),
            )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        filled_fields = {
            "job_id": job.job_id,
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip(),
            "email": profile.personal_info.email or "applicant@example.com",
            "phone": profile.personal_info.phone or "+919876543210",
        }
        application.form_values = filled_fields
        application.status = ApplicationStatus.FILLED
        return filled_fields

    async def submit_application(self, application: Application) -> bool:
        req_url = f"{self.base_url}/apply"
        try:
            payload = json.dumps(application.form_values or {}).encode("utf-8")
            req = urllib.request.Request(
                req_url, data=payload, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode())
                    submission_id = res_data.get("submission_id")
                    if application.form_values is None:
                        application.form_values = {}
                    application.form_values["submission_id"] = submission_id
                    application.status = ApplicationStatus.SUBMITTED
                    return True
        except Exception as exc:
            application.status = ApplicationStatus.FAILED
            application.error_message = str(exc)
            return False
        return False

    async def verify_submission(self, application: Application) -> bool:
        submission_id = (
            application.form_values.get("submission_id") if application.form_values else None
        )
        if not submission_id:
            application.status = ApplicationStatus.FAILED
            return False

        req_url = f"{self.base_url}/verify/{submission_id}"
        try:
            req = urllib.request.Request(req_url)
            with urllib.request.urlopen(req) as resp:
                if resp.status == 200:
                    application.status = ApplicationStatus.VERIFIED
                    return True
        except Exception as exc:
            application.status = ApplicationStatus.FAILED
            application.error_message = str(exc)
            return False
        return False
