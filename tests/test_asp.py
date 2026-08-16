import tempfile
from pathlib import Path
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_asp_closed_loop_autonomous():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter()
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(
                first_name="Rahul",
                last_name="Sharma",
                email="rahul@example.com",
                phone="+919876543210",
            ),
        )

        app_result = await pipeline.execute("http://127.0.0.1:5000/job/1", profile, auto_approve=True)

        assert app_result.status == ApplicationStatus.VERIFIED
        assert app_result.form_values["email"] == "rahul@example.com"
        assert len(app_result.evidence) > 0


@pytest.mark.asyncio
async def test_asp_supervised_approval_gate():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter()
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(first_name="Rahul", email="rahul@example.com"),
        )

        # Supervised mode (auto_approve = False) pauses at PENDING_APPROVAL
        app_result = await pipeline.execute("http://127.0.0.1:5000/job/1", profile, auto_approve=False)

        assert app_result.status == ApplicationStatus.PENDING_APPROVAL
