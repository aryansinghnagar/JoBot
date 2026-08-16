from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, PipelinePhase, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_integration_12_phase_dod_verification(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "p12_verify.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p12_prof",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_p12@example.com",
                phone="+917827756669",
            ),
        )

        job_url = f"{live_mock_ats_server}/jobs/2"
        app = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app.job_id == "2"
        assert app.status in [ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED]
        assert app.form_values.get("name") == "Aryan Nagar"


@pytest.mark.asyncio
async def test_integration_12_phase_evidence_collection(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "p12_evidence.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p12_ev_prof",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_ev@example.com",
                phone="+917827756669",
            ),
        )

        job_url = f"{live_mock_ats_server}/jobs/1"
        app = await pipeline.execute(job_url, profile, auto_approve=True)

        assert len(app.evidence) >= 1
        ev_steps = [e.step_name for e in app.evidence]
        assert "phase_11_submit" in ev_steps or "phase_12_verify" in ev_steps
