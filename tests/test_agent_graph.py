"""Unit tests for Multi-Agent Drafter-Evaluator State Graph (Phase 3)."""

from unittest.mock import AsyncMock, patch

import pytest

from jobot.ai.agent_graph import run_tailoring_graph
from jobot.models.domain import (
    CompensationDetails,
    JobPosting,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)


@pytest.mark.asyncio
async def test_agent_graph_execution():
    profile = UserProfile(
        personal_info=PersonalInfo(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="+1234567890",
            location="San Francisco, CA",
            summary="Experienced Python engineer with distributed systems background.",
        ),
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        work_experience=[
            WorkExperience(
                company="Tech Corp",
                title="Senior Software Engineer",
                start_date="2020-01-01",
                end_date=None,
                highlights=["Built distributed APIs in Python", "Maintained PostgreSQL database"],
            )
        ],
        compensation=CompensationDetails(target_base=180000, min_base=150000),
    )

    job = JobPosting(
        job_id="job-123",
        site="greenhouse",
        title="Backend Engineer",
        company="Stripe",
        url="https://boards.greenhouse.io/stripe/jobs/123",
        description="Looking for an engineer with strong Python and distributed systems experience.",
    )

    with patch("jobot.ai.router.ModelRouter.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '{"summary": "Experienced Python engineer with distributed systems background.", "skills": ["Python", "Docker"], "experience": []}'
        state = await run_tailoring_graph(profile, job, max_steps=4)
        assert state["step_count"] > 0
        assert state["tailored_text"] != ""
        assert state["rubric_grade"] in ("A", "B", "C", "D")
        assert state["next_node"] == "end"
