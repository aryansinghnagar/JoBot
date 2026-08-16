from pathlib import Path
import tempfile
import threading
import time
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager
# Uses live_live_mock_ats_server session fixture from conftest.py


@pytest.mark.asyncio
async def test_asp_closed_loop_autonomous(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="asp_test@example.com",
                phone="+919876543210",
            ),
        )

        app_result = await pipeline.execute(f"{live_mock_ats_server}/jobs/1", profile, auto_approve=True)

        assert app_result.status == ApplicationStatus.VERIFIED
        assert app_result.form_values["email"] == "asp_test@example.com"
        assert len(app_result.evidence) > 0


@pytest.mark.asyncio
async def test_asp_supervised_approval_gate(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(first_name="Aryan", email="aryan@example.com"),
        )

        # Supervised mode (auto_approve = False) pauses at PENDING_APPROVAL
        app_result = await pipeline.execute(f"{live_mock_ats_server}/jobs/1", profile, auto_approve=False)

        assert app_result.status == ApplicationStatus.PENDING_APPROVAL
