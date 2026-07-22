from datetime import datetime, timezone
import pytest
from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobot.policy.engine import PolicyEngine


def test_policy_engine_daily_limit_and_sensitive_exclusion():
    engine = PolicyEngine()
    engine.daily_application_limits["mock_ats"] = 2

    job = JobPosting(
        job_id="j1",
        site="mock_ats",
        url="http://localhost/1",
        title="Software Engineer",
        company="Acme Corp",
        description="We need your Aadhaar number for initial verification.",
    )

    profile = UserProfile(
        profile_id="p1",
        personal_info=PersonalInfo(first_name="Aryan", email="aryan@example.com"),
    )

    app = Application(
        application_id="a1",
        job_id="j1",
        site="mock_ats",
        idempotency_key="key1",
        status=ApplicationStatus.INTENT,
    )

    # Over daily limit check
    res_limit = engine.check_application_policy(job, profile, app, daily_submitted_count=2)
    assert res_limit.allowed is False
    assert "Daily limit" in (res_limit.blocking_reason or "")

    # Sensitive data exclusion check
    res_sensitive = engine.check_application_policy(job, profile, app, daily_submitted_count=0)
    assert res_sensitive.allowed is False
    assert "sensitive credentials" in (res_sensitive.blocking_reason or "")
