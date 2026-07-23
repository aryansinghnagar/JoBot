from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import ApplicationStatus, PersonalInfo, UserProfile
from jobot.obs.alerts import AlertDispatcher
from jobot.stealth.circuit_breaker import CircuitBreaker
from jobot.storage.db import DatabaseManager


class FailingIntegrationAdapter(MockATSAdapter):
    async def submit_application(self, application):
        raise RuntimeError("ATS endpoint HTTP 503 Service Unavailable")


@pytest.mark.asyncio
async def test_integration_circuit_breaker_trips_to_open(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "cb_int.db")
        alert_file = Path(tmpdir) / "cb_alerts.jsonl"
        dispatcher = AlertDispatcher(alert_file=alert_file)
        cb = CircuitBreaker(failure_threshold=2, max_retries=1, backoff_factor=0.01, alert_dispatcher=dispatcher)
        adapter = FailingIntegrationAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, circuit_breaker=cb)

        profile = UserProfile(
            profile_id="p_cb_int",
            personal_info=PersonalInfo(first_name="Aryan", email="cb_int@example.com"),
        )

        res1 = await pipeline.execute(f"{live_mock_ats_server}/jobs/1", profile, auto_approve=True)
        assert res1.status == ApplicationStatus.FAILED

        res2 = await pipeline.execute(f"{live_mock_ats_server}/jobs/2", profile, auto_approve=True)
        assert res2.status == ApplicationStatus.FAILED

        assert cb.get_state("mock_ats") == "OPEN"


@pytest.mark.asyncio
async def test_integration_circuit_breaker_dispatches_alert(live_mock_ats_server):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = DatabaseManager(Path(tmpdir) / "cb_alert_int.db")
        alert_file = Path(tmpdir) / "cb_alert_test.jsonl"
        dispatcher = AlertDispatcher(alert_file=alert_file)
        cb = CircuitBreaker(failure_threshold=1, max_retries=1, backoff_factor=0.01, alert_dispatcher=dispatcher)
        adapter = FailingIntegrationAdapter(base_url=live_mock_ats_server)
        pipeline = ApplicationSubmissionPipeline(adapter, db, circuit_breaker=cb)

        profile = UserProfile(
            profile_id="p_cb_alert",
            personal_info=PersonalInfo(first_name="Aryan", email="cb_alert@example.com"),
        )

        await pipeline.execute(f"{live_mock_ats_server}/jobs/1", profile, auto_approve=True)

        alerts = dispatcher.list_alerts()
        assert len(alerts) >= 1
        alert_titles = [a["title"] for a in alerts]
        assert any("Circuit Breaker OPEN" in t for t in alert_titles)
