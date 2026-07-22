from pathlib import Path
import tempfile
import threading
import time
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager
from tests.mock_ats.server import app as flask_app


@pytest.fixture(scope="module")
def mock_ats_server():
    server_thread = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1", port=5800, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1.0)
    yield "http://127.0.0.1:5800"


@pytest.mark.asyncio
async def test_asp_closed_loop_autonomous(mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter(base_url=mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan@example.com",
                phone="+919876543210",
            ),
        )

        app_result = await pipeline.execute(f"{mock_ats_server}/jobs/1", profile, auto_approve=True)

        assert app_result.status == ApplicationStatus.VERIFIED
        assert app_result.form_values["email"] == "aryan@example.com"
        assert len(app_result.evidence) > 0


@pytest.mark.asyncio
async def test_asp_supervised_approval_gate(mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test.db")
        adapter = MockATSAdapter(base_url=mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, Path(tmpdir) / "artifacts")

        profile = UserProfile(
            profile_id="asp_test",
            personal_info=PersonalInfo(first_name="Aryan", email="aryan@example.com"),
        )

        # Supervised mode (auto_approve = False) pauses at PENDING_APPROVAL
        app_result = await pipeline.execute(f"{mock_ats_server}/jobs/1", profile, auto_approve=False)

        assert app_result.status == ApplicationStatus.PENDING_APPROVAL
