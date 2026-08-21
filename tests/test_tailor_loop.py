"""Phase 3 T3.2/T3.3: drafter+reviewer loop, truthfulness gate, cover letters."""

import json

import pytest

from jobot.documents import CoverLetterGenerator, DocumentTailor, list_tones
from jobot.documents.tailor import verify_fact_truthfulness_detailed
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import (
    CompensationDetails,
    JobPosting,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)

JOB = JobPosting(
    job_id="j_t",
    site="naukri",
    url="https://naukri.com/job/1",
    title="Senior Python Engineer",
    company="Acme Corp",
    location="Bangalore",
    parsed_skills=["Python", "FastAPI"],
)

DRAFT_JSON = json.dumps(
    {
        "summary": "Backend engineer with 5 years building Python services.",
        "skills": ["Python", "FastAPI"],
        "experience": [
            {
                "company": "Acme",
                "title": "Senior Engineer",
                "bullets": ["Built REST APIs in Python with FastAPI."],
            }
        ],
    }
)

REVIEW_PASS_JSON = json.dumps(
    {
        "scores": {
            "accuracy": 5,
            "relevance": 5,
            "ats_friendliness": 5,
            "truthfulness": 5,
            "length": 4,
        },
        "issues": [],
        "verdict": "PASS",
    }
)

REVIEW_REVISE_JSON = json.dumps(
    {
        "scores": {
            "accuracy": 3,
            "relevance": 3,
            "ats_friendliness": 3,
            "truthfulness": 3,
            "length": 3,
        },
        "issues": ["Add more quantifiable impact"],
        "verdict": "REVISE",
    }
)


class FakeRouter:
    def __init__(self, drafts=None, reviews=None):
        self.drafts = list(drafts or [])
        self.reviews = list(reviews or [])
        self.calls = []

    async def generate_text(
        self, prompt, system_prompt=None, fallback_chain=None, task=None, **kwargs
    ):
        self.calls.append(task)
        if task == "resume_tailoring":
            return self.drafts.pop(0) if self.drafts else DRAFT_JSON
        if task == "resume_reviewer":
            return self.reviews.pop(0) if self.reviews else REVIEW_PASS_JSON
        return "I am excited to apply for this role. Regards, Aryan."


def profile(**overrides) -> UserProfile:
    kwargs = dict(
        profile_id="p_t",
        personal_info=PersonalInfo(
            first_name="Aryan", last_name="Sharma", email="aryan@example.com", phone="+91"
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI", "SQLite"],
        experiences=[
            WorkExperience(
                title="Senior Engineer",
                company="Acme",
                start_date="2021",
                end_date="Present",
                description="Built APIs in Python",
            )
        ],
    )
    kwargs.update(overrides)
    return UserProfile(**kwargs)


@pytest.mark.asyncio
async def test_tailor_loop_grounded_result():
    tailor = DocumentTailor(router=FakeRouter())
    result = await tailor.generate_tailored_materials(JOB, profile())

    assert result.is_truthful is True
    assert result.tailored_resume
    assert result.iteration_count == 1
    assert "Python" in result.highlighted_skills
    assert result.tailored_experience == [
        {
            "company": "Acme",
            "title": "Senior Engineer",
            "bullets": ["Built REST APIs in Python with FastAPI."],
        }
    ]
    assert result.cover_letter_text


@pytest.mark.asyncio
async def test_tailor_loop_revises_until_pass():
    router = FakeRouter(reviews=[REVIEW_REVISE_JSON, REVIEW_PASS_JSON])
    tailor = DocumentTailor(router=router)
    result = await tailor.generate_tailored_materials(JOB, profile())

    assert result.iteration_count == 2
    assert result.is_truthful is True


def test_verify_detects_skill_invention():
    ok, notes = verify_fact_truthfulness_detailed(
        "Expert in Kubernetes and Docker.", profile(), JOB
    )
    assert ok is False
    assert any("kubernetes" in n.lower() for n in notes)


def test_verify_grounded_skills_pass():
    ok, notes = verify_fact_truthfulness_detailed("Skilled in Python and FastAPI.", profile(), JOB)
    assert ok is True
    assert notes == []


def test_verify_detects_years_inflation():
    p = profile(custom_qa_answers={"Years of Experience": "5"})
    ok, notes = verify_fact_truthfulness_detailed("10 years of backend experience", p, JOB)
    assert ok is False
    assert any("years" in n for n in notes)


def test_verify_detects_email_mismatch():
    ok, notes = verify_fact_truthfulness_detailed("Contact me at other@mail.com", profile(), JOB)
    assert ok is False
    assert any("email" in n for n in notes)


@pytest.mark.asyncio
async def test_degradation_fallback_stays_truthful():
    class DegradedRouter(FakeRouter):
        async def generate_text(
            self, prompt, system_prompt=None, fallback_chain=None, task=None, **kwargs
        ):
            return DEGRADATION_TEXT

    tailor = DocumentTailor(router=DegradedRouter())
    result = await tailor.generate_tailored_materials(JOB, profile())

    assert result.is_truthful is True
    assert set(result.highlighted_skills) <= set(profile().skills)


@pytest.mark.asyncio
async def test_cover_letter_tones_and_length_cap():
    router = FakeRouter()
    gen = CoverLetterGenerator(router=router)
    for tone in list_tones():
        letter = await gen.generate(JOB, profile(), matching_skills=["Python"], tone=tone)
        assert letter
    with pytest.raises(ValueError):
        await gen.generate(JOB, profile(), tone="nope")


@pytest.mark.asyncio
async def test_cover_letter_extra_prompt_passthrough():
    router = FakeRouter()
    gen = CoverLetterGenerator(router=router)
    await gen.generate(JOB, profile(), extra_prompt="Mention Bengaluru")
    prompt = router.calls  # cover_letter task called
    assert "cover_letter" in prompt
