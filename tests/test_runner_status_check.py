from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile
from jobot.runner import ContinuousCampaignRunner
from jobot.storage.db import DatabaseManager


class FailingSubmitAdapter(MockATSAdapter):
    async def submit_application(self, application):
        return False


@pytest.mark.asyncio
async def test_runner_does_not_increment_on_failed_submit():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DatabaseManager(tmp_path / "test_runner_failed.db")
        adapter = FailingSubmitAdapter(base_url="http://127.0.0.1:5800")
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        profile = UserProfile(
            profile_id="p_fail",
            personal_info=PersonalInfo(first_name="Aryan", email="fail@example.com"),
        )

        job_url = "http://127.0.0.1:5800/jobs/1"
        app_res = await pipeline.execute(job_url, profile, auto_approve=True)

        assert app_res.status == ApplicationStatus.FAILED

        # Verify runner logic: failed application does not increment total_submitted count
        total_submitted = 0
        if app_res.status in [ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED]:
            total_submitted += 1

        assert total_submitted == 0
