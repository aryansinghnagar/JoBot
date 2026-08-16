"""Unit tests for CXS and ATS adapter family (UC-15 & UC-16)."""

import pytest
from jobot.adapters.cxs import (
    AshbyAdapter,
    BambooHRAdapter,
    RecruiteeAdapter,
    TeamtailorAdapter,
    WorkableAdapter,
)
from jobot.adapters.registry import AdapterRegistry, infer_site
from jobot.models.domain import Application, JobPosting, PersonalInfo, UserProfile


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        profile_id="test_candidate",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="aryan@example.com",
            phone="+919876543210",
            location_city="Bengaluru",
        ),
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
    )


@pytest.mark.parametrize(
    "adapter_cls,site_name,test_url",
    [
        (AshbyAdapter, "ashby", "https://jobs.ashbyhq.com/openai/12345-6789-abcdef"),
        (WorkableAdapter, "workable", "https://apply.workable.com/spotify/j/ABCDEF1234/"),
        (RecruiteeAdapter, "recruitee", "https://hotjar.recruitee.com/o/senior-backend-engineer"),
        (TeamtailorAdapter, "teamtailor", "https://jobs.teamtailor.com/jobs/1234567"),
        (BambooHRAdapter, "bamboohr", "https://stripe.bamboohr.com/careers/99"),
    ],
)
@pytest.mark.asyncio
async def test_cxs_adapter_lifecycle(
    adapter_cls, site_name: str, test_url: str, sample_profile: UserProfile
):
    # Verify adapter registration and site inference
    assert infer_site(test_url) == site_name
    adapter = AdapterRegistry.get_adapter(site_name)
    assert isinstance(adapter, adapter_cls)

    # 1. Parse Job Posting
    job = await adapter.parse_job_posting(test_url)
    assert isinstance(job, JobPosting)
    assert job.site == site_name
    assert len(job.parsed_skills) > 0

    # 2. Fill Form
    app = Application(
        application_id=f"app_{site_name}_001",
        job_id=job.job_id,
        user_profile_id=sample_profile.profile_id,
        site=site_name,
        idempotency_key=f"idem_{site_name}_001",
    )
    filled = await adapter.fill_form(job, sample_profile, app)
    assert filled is not None
    assert app.status.value == "filled"

    # 3. Submit
    submitted = await adapter.submit_application(app)
    assert submitted is True
    assert app.status.value == "submitted"

    # 4. Verify
    verif = await adapter.verify_submission(app)
    assert verif.success is True
    assert verif.confirmation_id is not None
