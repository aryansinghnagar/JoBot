"""Tests for SkillGapAnalyzer event-loop safety and async API (JOB-AUD-002)."""

from unittest.mock import AsyncMock, patch

import pytest

from jobot.analytics.skill_gap import SkillGap, SkillGapAnalyzer
from jobot.models.domain import CompensationDetails, JobPosting, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


def _sample_profile() -> UserProfile:
    return UserProfile(
        personal_info=PersonalInfo(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="+1234567890",
            location_city="Bengaluru",
            location_country="India",
        ),
        compensation=CompensationDetails(),
        skills=["Python", "FastAPI"],
    )


@pytest.mark.asyncio
async def test_sync_analyze_inside_running_event_loop_does_not_crash(tmp_path):
    db = DatabaseManager(tmp_path / "skill_test.db")
    db.save_job_posting(
        JobPosting(
            job_id="j1",
            site="greenhouse",
            url="https://example.com/j1",
            title="Backend Dev",
            company="Acme",
            description="Need Docker, Kubernetes, Python",
            parsed_skills=["Docker", "Kubernetes", "Python"],
        )
    )

    analyzer = SkillGapAnalyzer(db=db)
    profile = _sample_profile()

    # Calling synchronous analyze() inside this async pytest test function
    # verifies that active event loop detection falls back to rule-based recommendations
    # without raising RuntimeError: This event loop is already running.
    report = analyzer.analyze(profile)
    assert report.total_postings == 1
    assert any(g.skill == "docker" for g in report.gaps)
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_analyze_async_uses_llm_recommendations(tmp_path):
    db = DatabaseManager(tmp_path / "skill_test2.db")
    db.save_job_posting(
        JobPosting(
            job_id="j2",
            site="lever",
            url="https://example.com/j2",
            title="SRE",
            company="Globex",
            description="Need Rust, Terraform",
            parsed_skills=["Rust", "Terraform"],
        )
    )

    analyzer = SkillGapAnalyzer(db=db)
    profile = _sample_profile()

    with patch.object(analyzer.router, "generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '["Master Rust memory management", "Build Terraform IaC modules"]'

        report = await analyzer.analyze_async(profile)
        assert report.total_postings == 1
        assert "Master Rust memory management" in report.recommendations
