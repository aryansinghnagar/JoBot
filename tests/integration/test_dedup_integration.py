from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.mark.asyncio
async def test_integration_dedup_skips_duplicate_submission(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "dedup_integ.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_dedup_int",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan_dedup@example.com",
                phone="+917827756669",
            ),
        )

        job_url = f"{live_mock_ats_server}/jobs/1"
        app1 = await pipeline.execute(job_url, profile, auto_approve=True)
        assert app1.status == ApplicationStatus.VERIFIED

        # Second attempt with same job_url and profile_id
        app2 = await pipeline.execute(job_url, profile, auto_approve=True)
        assert app2.status == ApplicationStatus.DUPLICATE_SKIPPED


@pytest.mark.asyncio
async def test_integration_idempotency_key_query(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "dedup_query.db")
        adapter = MockATSAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_ik_prof",
            personal_info=PersonalInfo(first_name="Aryan", email="ik@example.com"),
        )

        job_url = f"{live_mock_ats_server}/jobs/2"
        app = await pipeline.execute(job_url, profile, auto_approve=True)
        key = app.idempotency_key

        fetched_app = db.get_application_by_idempotency_key(key)
        assert fetched_app is not None
        assert fetched_app.application_id == app.application_id
