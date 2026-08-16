from pathlib import Path
import tempfile
import pytest
from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile
from jobot.obs.alerts import AlertDispatcher, AlertLevel
from jobot.policy.engine import PolicyEngine
from jobot.stealth.circuit_breaker import CircuitBreaker


def test_alert_dispatcher_persistence_and_acknowledgement():
    with tempfile.TemporaryDirectory() as tmpdir:
        alert_file = Path(tmpdir) / "alerts.jsonl"
        dispatcher = AlertDispatcher(alert_file=alert_file)

        msg = dispatcher.dispatch_alert("Test Alert", "Alert message content", level=AlertLevel.HIGH)
        assert msg.alert_id.startswith("ALT-")

        alerts = dispatcher.list_alerts()
        assert len(alerts) == 1
        assert alerts[0]["title"] == "Test Alert"
        assert alerts[0]["acknowledged"] is False

        ack_success = dispatcher.acknowledge_alert(msg.alert_id)
        assert ack_success is True

        unack_alerts = dispatcher.list_alerts(unack_only=True)
        assert len(unack_alerts) == 0


def test_policy_engine_dispatches_alert_on_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        alert_file = Path(tmpdir) / "policy_alerts.jsonl"
        dispatcher = AlertDispatcher(alert_file=alert_file)
        engine = PolicyEngine(alert_dispatcher=dispatcher)
        engine.daily_application_limits["mock_ats"] = 1

        job = JobPosting(
            job_id="j_pol",
            site="mock_ats",
            url="http://localhost/1",
            title="Backend Engineer",
            company="Acme",
        )
        profile = UserProfile(
            profile_id="p_pol",
            personal_info=PersonalInfo(first_name="Aryan", email="a@example.com"),
        )
        app = Application(
            application_id="app_pol",
            job_id="j_pol",
            site="mock_ats",
            idempotency_key="key_pol",
            status=ApplicationStatus.INTENT,
        )

        res = engine.check_application_policy(job, profile, app, daily_submitted_count=1)
        assert res.allowed is False

        alerts = dispatcher.list_alerts()
        assert len(alerts) == 1
        assert "Daily Limit Reached" in alerts[0]["title"]
