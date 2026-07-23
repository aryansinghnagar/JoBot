from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, TrustLevel, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_integration_autonomous_end_to_end(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "e2e_auto.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_e2e_auto",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_e2e@example.com",
                phone="+917827756669",
            ),
        )

        job_url = f"{live_mock_ats_server}/jobs/1"
        app = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app.status in [ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED]
        assert app.form_values["email"] == "aryan_e2e@example.com"
        assert len(app.evidence) >= 1


@pytest.mark.asyncio
async def test_integration_supervised_mode_approval_pause(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "e2e_sup.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_e2e_sup",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_sup@example.com",
                phone="+917827756669",
            ),
        )

        job_url = f"{live_mock_ats_server}/jobs/1"
        app = await pipeline.execute(job_url, profile, auto_approve=False)

        assert app.status == ApplicationStatus.PENDING_APPROVAL
        assert app.trust_level == TrustLevel.SUPERVISED
