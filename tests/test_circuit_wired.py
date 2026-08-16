from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.stealth.circuit_breaker import CircuitBreaker
from jobot.storage.db import DatabaseManager


class FailingSubmitAdapter(MockATSAdapter):
    async def submit_application(self, application):
        raise RuntimeError("ATS endpoint error")


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_3_failures():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_cb_wired.db")
        cb = CircuitBreaker(failure_threshold=3, max_retries=1, backoff_factor=0.01)
        adapter = FailingSubmitAdapter(base_url="http://127.0.0.1:5800")
        pipeline = ApplicationSubmissionPipeline(adapter, db, circuit_breaker=cb)

        profile = UserProfile(
            profile_id="p_cb3",
            personal_info=PersonalInfo(first_name="Aryan", email="cb3@example.com"),
        )

        job_url_1 = "http://127.0.0.1:5800/jobs/1"
        job_url_2 = "http://127.0.0.1:5800/jobs/2"
        job_url_3 = "http://127.0.0.1:5800/jobs/3"
        job_url_4 = "http://127.0.0.1:5800/jobs/4"

        # Attempt 1
        res1 = await pipeline.execute(job_url_1, profile, auto_approve=True)
        assert res1.status == ApplicationStatus.FAILED

        # Attempt 2
        res2 = await pipeline.execute(job_url_2, profile, auto_approve=True)
        assert res2.status == ApplicationStatus.FAILED

        # Attempt 3
        res3 = await pipeline.execute(job_url_3, profile, auto_approve=True)
        assert res3.status == ApplicationStatus.FAILED

        # Circuit should now be OPEN
        assert cb.get_state("mock_ats") == "OPEN"

        # Attempt 4: Should immediately be skipped with CIRCUIT_OPEN
        res4 = await pipeline.execute(job_url_4, profile, auto_approve=True)
        assert res4.status == ApplicationStatus.CIRCUIT_OPEN
