"""Cover letter generation with 5 tone presets (Phase 3, T3.3)."""

from typing import Dict, List, Optional

from jobot.ai.router import ModelRouter
from jobot.models.domain import JobPosting, UserProfile
from jobot.security.prompt_guard import sanitize_llm_input

TONE_PRESETS: Dict[str, Dict[str, object]] = {
    "classic": {
        "label": "Classic professional",
        "system_prompt": (
            "You are a professional cover letter writer. Write in a concise, formal, "
            "business tone. Ground every claim strictly in the candidate profile facts "
            "provided. Never invent skills, projects, employers, or numbers."
        ),
        "max_length": 350,
    },
    "narrative": {
        "label": "Narrative story-driven",
        "system_prompt": (
            "You are a cover letter writer. Write in a warm narrative voice that tells "
            "a short career story using ONLY profile facts. Never invent skills, "
            "projects, employers, or numbers."
        ),
        "max_length": 400,
    },
    "technical": {
        "label": "Technical detail-heavy",
        "system_prompt": (
            "You are a technical cover letter writer. Emphasize concrete technologies, "
            "tools, and depth of the candidate's actual skill set. Ground every claim "
            "strictly in the candidate profile facts. Never invent skills or projects."
        ),
        "max_length": 400,
    },
    "brief": {
        "label": "Brief and direct",
        "system_prompt": (
            "You are a cover letter writer. Write a very short, punchy, direct cover "
            "letter (under 150 words) using ONLY profile facts. No fluff, no invented "
            "facts."
        ),
        "max_length": 150,
    },
    "enthusiastic": {
        "label": "Energetic and positive",
        "system_prompt": (
            "You are a cover letter writer. Write with genuine enthusiasm and energy "
            "while remaining professional. Ground every claim strictly in the "
            "candidate profile facts. Never invent skills, projects, or numbers."
        ),
        "max_length": 350,
    },
}


def list_tones() -> List[str]:
    return list(TONE_PRESETS)


class CoverLetterGenerator:
    """Generates profile-grounded cover letters via ModelRouter."""

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()

    def _preset(self, tone: str) -> Dict[str, object]:
        if tone not in TONE_PRESETS:
            raise ValueError(f"Unknown tone '{tone}'. Available: {', '.join(list_tones())}")
        return TONE_PRESETS[tone]

    def _truncate(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        cut = text[:max_length]
        space = cut.rfind(" ")
        return (cut[:space] + " ..." if space > 0 else cut + "...").strip()

    async def generate(
        self,
        job: JobPosting,
        profile: UserProfile,
        matching_skills: Optional[List[str]] = None,
        tone: str = "classic",
        extra_prompt: str = "",
    ) -> str:
        preset = self._preset(tone)
        skills = matching_skills or [s for s in profile.skills]
        years = profile.custom_qa_answers.get("Years of Experience", "")
        facts = (
            f"Name: {profile.personal_info.first_name} {profile.personal_info.last_name}\n"
            f"Email: {profile.personal_info.email}\n"
            f"Phone: {profile.personal_info.phone}\n"
            f"Location: {profile.personal_info.location_city}, {profile.personal_info.location_country}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Notice period: {profile.compensation.notice_period_days} days\n"
        )
        if years:
            facts += f"Years of experience: {years}\n"
        if profile.experiences:
            facts += "Experience:\n" + "\n".join(
                f"- {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date or 'Present'})"
                for exp in profile.experiences
            )
        job_title = sanitize_llm_input(job.title)
        job_company = sanitize_llm_input(job.company)
        job_location = sanitize_llm_input(job.location)
        clean_skills = [sanitize_llm_input(s) for s in skills]
        clean_extra = sanitize_llm_input(extra_prompt) if extra_prompt else ""

        prompt = (
            f"Job Title: {job_title}\n"
            f"Company: {job_company}\n"
            f"Location: {job_location}\n\n"
            f"Candidate Profile Facts:\n{facts}\n\n"
            f"Relevant skills to highlight: {', '.join(clean_skills)}\n"
        )
        if clean_extra:
            prompt += f"Additional instructions: {clean_extra}\n"
        prompt += "\nWrite the cover letter now."

        letter = await self.router.generate_text(
            prompt,
            system_prompt=str(preset["system_prompt"]),
            task="cover_letter",
            temperature=0.7,
            max_tokens=int(str(preset["max_length"])) + 100,
        )
        return self._truncate(letter, int(str(preset["max_length"])))
