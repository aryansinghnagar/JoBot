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
async def test_mock_ats_integration_full_flow(mock_ats_server):
    adapter = MockATSAdapter(base_url=mock_ats_server)
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_integration.db")
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p1",
            personal_info=PersonalInfo(
                first_name="Aryan", last_name="Nagar", email="aryan@example.com"
            ),
        )

        job_url = f"{mock_ats_server}/jobs/1"
        app_res = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app_res.status == ApplicationStatus.VERIFIED
        assert app_res.form_values is not None
        assert app_res.form_values.get("submission_id") is not None
