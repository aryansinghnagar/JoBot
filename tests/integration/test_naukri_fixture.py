from pathlib import Path
import tempfile
import pytest

from jobot.adapters.naukri import NaukriAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_naukri_adapter_fixture_execution():
    fixture_html = Path("tests/fixtures/naukri/job_page.html")
    assert fixture_html.exists()

    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "nk_fixture.db")
        adapter = NaukriAdapter()
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_nk_fix",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_nk@example.com",
                phone="+917827756669",
            ),
        )

        job_url = "https://www.naukri.com/job-listings-senior-backend-engineer-101"
        app = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app.site == "naukri"
        assert app.status in [ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED]
        assert app.form_values.get("email") == "aryan_nk@example.com"
