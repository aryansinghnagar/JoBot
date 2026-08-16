import pytest
from jobot.models.domain import Application, ApplicationStatus, JobPosting, TrustLevel, UserProfile
from jobot.policy.engine import PolicyEngine


def test_policy_engine_daily_limit():
    policy = PolicyEngine()
    job = JobPosting(
        job_id="j1",
        site="linkedin",
        url="https://linkedin.com/jobs/1",
        title="Engineer",
        company="Co",
    )
    profile = UserProfile()
    app = Application(
        application_id="a1",
        job_id="j1",
        site="linkedin",
        idempotency_key="k1",
        trust_level=TrustLevel.AUTONOMOUS,
    )

    # Exceeding daily cap (limit for linkedin is 100)
    violations = policy.evaluate_application_policy(job, profile, app, daily_submitted_count=101)
    assert len(violations) > 0
    assert violations[0].policy_name == "POLICY_MAX_DAILY_APPLICATIONS"


def test_policy_engine_sensitive_data_exclusion():
    policy = PolicyEngine()
    job = JobPosting(
        job_id="j2",
        site="naukri",
        url="https://naukri.com/job/2",
        title="Developer",
        company="Co",
        description="Please provide your Aadhaar Number for verification.",
    )
    profile = UserProfile()
    app = Application(
        application_id="a2",
        job_id="j2",
        site="naukri",
        idempotency_key="k2",
        trust_level=TrustLevel.AUTONOMOUS,
    )

    violations = policy.evaluate_application_policy(job, profile, app, daily_submitted_count=0)
    assert any(v.policy_name == "POLICY_SENSITIVE_DATA_EXCLUSION" for v in violations)
