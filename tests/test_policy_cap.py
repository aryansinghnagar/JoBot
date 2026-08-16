from pathlib import Path
import tempfile
import pytest

from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobot.policy.engine import PolicyEngine


def test_policy_engine_blocks_after_daily_cap():
    engine = PolicyEngine()
    engine.daily_application_limits["linkedin"] = 2

    job = JobPosting(
        job_id="j_cap",
        site="linkedin",
        url="https://linkedin.com/jobs/123",
        title="Software Engineer",
        company="TechCorp",
    )
    profile = UserProfile(
        profile_id="p_cap",
        personal_info=PersonalInfo(first_name="Aryan", email="cap@example.com"),
    )
    app = Application(
        application_id="app_cap",
        job_id="j_cap",
        site="linkedin",
        idempotency_key="key_cap",
        status=ApplicationStatus.INTENT,
    )

    res1 = engine.check_application_policy(job, profile, app, daily_submitted_count=0)
    assert res1.allowed is True

    res2 = engine.check_application_policy(job, profile, app, daily_submitted_count=1)
    assert res2.allowed is True

    res3 = engine.check_application_policy(job, profile, app, daily_submitted_count=2)
    assert res3.allowed is False
    assert "Daily limit of 2 applications reached" in res3.blocking_reason
