from pathlib import Path
import tempfile
import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.stealth.circuit_breaker import CircuitBreaker
from jobot.storage.db import DatabaseManager


class FailingAdapter(MockATSAdapter):
    async def submit_application(self, application):
        raise RuntimeError("Portal connection timeout")


@pytest.mark.asyncio
async def test_circuit_breaker_opens_in_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "test_cb.db")
        cb = CircuitBreaker(failure_threshold=2, max_retries=1, backoff_factor=0.01)
        adapter = FailingAdapter(base_url="http://127.0.0.1:5800")
        pipeline = ApplicationSubmissionPipeline(adapter, db, circuit_breaker=cb)

        profile = UserProfile(
            profile_id="p_cb",
            personal_info=PersonalInfo(first_name="Aryan", email="cb@example.com"),
        )

        job_url = "http://127.0.0.1:5800/jobs/1"
        res1 = await pipeline.execute(job_url, profile, auto_approve=True)
        assert res1.status == ApplicationStatus.FAILED

        res2 = await pipeline.execute(job_url, profile, auto_approve=True)
        assert res2.status == ApplicationStatus.FAILED

        assert cb.get_state("mock_ats") == "OPEN"

        res3 = await pipeline.execute(job_url, profile, auto_approve=True)
        assert res3.status == ApplicationStatus.CIRCUIT_OPEN
        assert "OPEN" in (res3.error_message or "")
