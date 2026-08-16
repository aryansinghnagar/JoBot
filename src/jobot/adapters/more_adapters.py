import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from jobot.adapters.base import SiteAdapter
from jobot.ai.skill_extractor import SkillExtractor
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile


class GenericPortalAdapter(SiteAdapter):
    def __init__(self, site_name: str):
        super().__init__(site_name)

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        await asyncio.sleep(0.1)
        desc = f"Requirement for Software Engineer on {self.site_name.capitalize()} with expertise in Python, FastAPI, React, PostgreSQL, Docker, and CI/CD."
        skills = SkillExtractor().extract_skills_sync(desc)
        return JobPosting(
            job_id=str(uuid.uuid4()),
            site=self.site_name,
            url=url,
            title=f"Engineer on {self.site_name.capitalize()}",
            company=f"{self.site_name.capitalize()} Hiring Partner",
            location="India",
            description=desc,
            parsed_skills=skills,
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        await asyncio.sleep(0.3)
        filled = {
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}",
            "email": profile.personal_info.email,
            "phone": profile.personal_info.phone,
        }
        application.form_values = filled
        application.status = ApplicationStatus.FILLED
        return filled

    async def submit_application(self, application: Application) -> bool:
        await asyncio.sleep(0.3)
        application.status = ApplicationStatus.SUBMITTED
        return True

    async def verify_submission(self, application: Application) -> bool:
        await asyncio.sleep(0.2)
        application.status = ApplicationStatus.VERIFIED
        return True


class GlassdoorAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("glassdoor")


class ZipRecruiterAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("ziprecruiter")


class ShineAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("shine")


class FounditAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("foundit")


class HiristAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("hirist")


class InstahyreAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("instahyre")


class CutshortAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("cutshort")


class WellfoundAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("wellfound")


class SmartRecruitersAdapter(GenericPortalAdapter):
    def __init__(self):
        super().__init__("smartrecruiters")
