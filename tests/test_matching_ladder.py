"""Unit tests for the 4-Stage Matching Ladder (UC-23)."""

import pytest
from jobot.discovery.matching_ladder import MatchingLadder, MatchingLadderResult
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.models.domain import (
    CompensationDetails,
    Education,
    JobPosting,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)


@pytest.fixture
def candidate_profile() -> UserProfile:
    return UserProfile(
        profile_id="aryan",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="aryan@example.com",
            phone="9876543210",
            location_city="Bengaluru",
            location_state="Karnataka",
        ),
        experiences=[
            WorkExperience(
                company="Alpha Systems",
                title="Software Engineer",
                start_date="2022-01",
                end_date="2025-01",
                description="Engineered high throughput distributed microservices using Python, FastAPI, and PostgreSQL.",
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
            )
        ],
        education=[
            Education(
                institution="IIT Bombay",
                degree="B.Tech",
                field_of_study="EE",
                start_year=2018,
                end_year=2022,
            )
        ],
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "Distributed Systems"],
        compensation=CompensationDetails(
            current_ctc_inr=1500000.0,
            expected_ctc_inr=2400000.0,
            notice_period_days=30,
        ),
    )


@pytest.fixture
def matching_posting() -> JobPosting:
    return JobPosting(
        job_id="job_001",
        site="mock_ats",
        url="https://jobs.example.com/p/1",
        title="Senior Python Backend Engineer",
        company="NexTech",
        location="Bengaluru, Karnataka",
        experience_required="3-5 years",
        description="Looking for an experienced engineer skilled in Python, FastAPI, PostgreSQL, and Docker.",
        parsed_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
    )


@pytest.fixture
def mismatch_location_posting() -> JobPosting:
    return JobPosting(
        job_id="job_002",
        site="mock_ats",
        url="https://jobs.example.com/p/2",
        title="Python Developer",
        company="LondonCorp",
        location="London, UK (On-site)",
        experience_required="2 years",
        description="Onsite developer needed in London office. Python required.",
        parsed_skills=["Python"],
    )


@pytest.mark.asyncio
async def test_matching_ladder_high_fit(
    candidate_profile: UserProfile, matching_posting: JobPosting
):
    ladder = MatchingLadder()
    result = await ladder.evaluate_ladder(
        matching_posting, candidate_profile, target_location="Bengaluru", include_llm_stage=False
    )
    assert result.passed_hard_filters is True
    assert result.skill_score >= 0.8
    assert result.composite_score >= 0.6
    assert result.recommendation in ("HIGH_FIT", "MEDIUM_FIT")
    assert "Python" in result.matching_skills
    assert "FastAPI" in result.matching_skills


@pytest.mark.asyncio
async def test_matching_ladder_hard_filter_location_rejection(
    candidate_profile: UserProfile, mismatch_location_posting: JobPosting
):
    ladder = MatchingLadder()
    result = await ladder.evaluate_ladder(
        mismatch_location_posting,
        candidate_profile,
        target_location="Bengaluru",
        include_llm_stage=False,
    )
    assert result.passed_hard_filters is False
    assert result.recommendation == "FILTERED_OUT"
    assert any("Location mismatch" in r for r in result.hard_filter_reasons)


@pytest.mark.asyncio
async def test_discovery_engine_evaluate_ladder_integration(
    candidate_profile: UserProfile, matching_posting: JobPosting
):
    engine = JobDiscoveryEngine()
    result = await engine.evaluate_ladder(
        matching_posting, candidate_profile, target_location="Bengaluru", include_llm_stage=False
    )
    assert isinstance(result, MatchingLadderResult)
    assert result.passed_hard_filters is True
    assert result.composite_score > 0.0
