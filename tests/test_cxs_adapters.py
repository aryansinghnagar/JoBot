"""Unit tests for CXS and ATS adapter family — post-audit discovery-only contract.

After the safety audit, CXS adapters (Ashby, Workable, Recruitee, Teamtailor,
BambooHR) are discovery/parse-only.  submit_application() and
verify_submission() must raise AdapterCapabilityError.
"""

import pytest

from jobot.adapters.capabilities import AdapterCapability, AdapterCapabilityError
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
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            phone="+1-555-0100",
            location_city="San Francisco",
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
async def test_cxs_adapter_discovery_only(
    adapter_cls, site_name: str, test_url: str, sample_profile: UserProfile
):
    # Verify adapter registration and site inference
    assert infer_site(test_url) == site_name
    adapter = AdapterRegistry.get_adapter(site_name)
    assert isinstance(adapter, adapter_cls)

    # Verify capabilities are declared as discovery-only
    assert adapter.capabilities == AdapterCapability.DISCOVERY_PARSE

    # 1. Parse Job Posting — still works (URL metadata extraction)
    job = await adapter.parse_job_posting(test_url)
    assert isinstance(job, JobPosting)
    assert job.site == site_name
    assert isinstance(job.parsed_skills, list)

    # 2. Fill Form — must raise
    app = Application(
        application_id=f"app_{site_name}_001",
        job_id=job.job_id,
        user_profile_id=sample_profile.profile_id,
        site=site_name,
        idempotency_key=f"idem_{site_name}_001",
    )
    with pytest.raises(AdapterCapabilityError, match="fill_form"):
        await adapter.fill_form(job, sample_profile, app)

    # 3. Submit — must raise
    with pytest.raises(AdapterCapabilityError, match="submit_application"):
        await adapter.submit_application(app)

    # 4. Verify — must raise
    with pytest.raises(AdapterCapabilityError, match="verify_submission"):
        await adapter.verify_submission(app)
