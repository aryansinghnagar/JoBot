from pathlib import Path
import tempfile
import pytest

from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobot.policy.engine import PolicyEngine


@pytest.mark.asyncio
async def test_integration_policy_daily_cap_enforcement(live_mock_ats_server):
    engine = PolicyEngine()
    engine.daily_application_limits["mock_ats"] = 1

    job = JobPosting(
        job_id="j_pol_int",
        site="mock_ats",
        url=f"{live_mock_ats_server}/jobs/1",
        title="AI Engineer",
        company="MockCorp",
    )
    profile = UserProfile(
        profile_id="p_pol_int",
        personal_info=PersonalInfo(first_name="Aryan", email="pol_int@example.com"),
    )
    app = Application(
        application_id="app_pol_int",
        job_id="j_pol_int",
        site="mock_ats",
        idempotency_key="key_pol_int",
        status=ApplicationStatus.INTENT,
    )

    res = engine.check_application_policy(job, profile, app, daily_submitted_count=1)
    assert res.allowed is False
    assert "Daily limit of 1 applications reached" in res.blocking_reason


@pytest.mark.asyncio
async def test_integration_policy_sensitive_data_protection(live_mock_ats_server):
    from jobot.ai.qa_engine import QAEngine, QuestionType
    qa = QAEngine()

    q_type = qa.classify_question("Please submit your Aadhaar number and SSN")
    assert q_type == QuestionType.SENSITIVE

    res = await qa.answer_question("Please submit your Aadhaar number and SSN", UserProfile(profile_id="p_sens"))
    assert res.requires_user_approval is True
    assert res.answer == "[SENSITIVE_FIELD_PAUSED]"
