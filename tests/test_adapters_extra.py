import pytest
from jobot.adapters import GreenhouseAdapter, IndeedAdapter, LeverAdapter, LinkedInAdapter
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile


@pytest.mark.asyncio
async def test_all_site_adapters():
    adapters = [
        LinkedInAdapter(),
        IndeedAdapter(),
        GreenhouseAdapter(),
        LeverAdapter(),
    ]

    profile = UserProfile(
        profile_id="adapter_test",
        personal_info=PersonalInfo(first_name="Rahul", last_name="Sharma", email="rahul@example.com"),
    )

    for adapter in adapters:
        assert await adapter.login() is True
        job = await adapter.parse_job_posting(f"https://{adapter.site_name}.example.com/job/101")
        assert job.site == adapter.site_name

        app = Application(
            application_id="app_test",
            job_id=job.job_id,
            site=adapter.site_name,
            idempotency_key=f"idempotency_{adapter.site_name}",
        )

        filled_data = await adapter.fill_form(job, profile, app)
        assert app.status == ApplicationStatus.FILLED
        assert filled_data.get("email") == "rahul@example.com" or filled_data.get("applicant_email") == "rahul@example.com"

        assert await adapter.submit_application(app) is True
        assert await adapter.verify_submission(app) is True
