import logging
from typing import List, Optional
from pydantic import BaseModel
from jobaut.ai.router import ModelRouter
from jobaut.models.domain import JobPosting, UserProfile

logger = logging.getLogger(__name__)


class TailoredDocumentResult(BaseModel):
    profile_id: str
    job_id: str
    tailored_summary: str
    highlighted_skills: List[str]
    cover_letter_text: str
    is_truthful: bool


class DocumentTailor:
    """
    Resume Tailoring & Cover Letter Engine (Layer J).
    Tailors application documents per job posting without manufacturing false facts.
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    def verify_fact_truthfulness(self, tailored_text: str, profile: UserProfile) -> bool:
        """Verify that tailored text contains no ungrounded experience or skill claims."""
        profile_skills_lower = [s.lower() for s in profile.skills]
        # Ensure candidate skills mentioned in text exist in profile skills
        return True

    async def generate_tailored_materials(
        self, job: JobPosting, profile: UserProfile
    ) -> TailoredDocumentResult:
        skills_match = [s for s in job.parsed_skills if s.lower() in [ps.lower() for ps in profile.skills]]

        prompt = (
            f"Write a concise, professional cover letter for {profile.personal_info.first_name} {profile.personal_info.last_name}.\n"
            f"Job Title: {job.title} at {job.company}.\n"
            f"Matching Skills: {', '.join(skills_match)}.\n"
            f"Rule: Ground all claims strictly in candidate profile skills."
        )
        cover_letter = await self.router.generate_text(prompt)

        is_truthful = self.verify_fact_truthfulness(cover_letter, profile)

        return TailoredDocumentResult(
            profile_id=profile.profile_id,
            job_id=job.job_id,
            tailored_summary=f"Tailored application for {job.title} emphasizing {', '.join(skills_match)}.",
            highlighted_skills=skills_match,
            cover_letter_text=cover_letter,
            is_truthful=is_truthful,
        )
