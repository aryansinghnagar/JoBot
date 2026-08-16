"""Unit tests for SiteHealthMonitor and CLI command (UC-13)."""

from typer.testing import CliRunner

from jobot.cli.main import app
from jobot.stealth.site_health import SiteHealthMonitor

runner = CliRunner()


def test_site_health_monitor_transitions():
    monitor = SiteHealthMonitor(failure_trip_threshold=3)
    st = monitor.get_status("ashby")
    assert st.status == "HEALTHY"
    assert st.success_rate == 1.0

    monitor.record_success("ashby", latency_ms=120.0)
    assert st.success_count == 1
    assert st.avg_latency_ms == 120.0

    # 1 failure -> still HEALTHY
    monitor.record_failure("ashby", "HTTP 500")
    assert st.consecutive_failures == 1
    assert st.status == "HEALTHY"

    # 2 failures -> DEGRADED
    monitor.record_failure("ashby", "HTTP 502")
    assert st.consecutive_failures == 2
    assert st.status == "DEGRADED"

    # 3 failures -> TRIPPED
    monitor.record_failure("ashby", "HTTP 503")
    assert st.consecutive_failures == 3
    assert st.status == "TRIPPED"

    # Success recovers to HEALTHY
    monitor.record_success("ashby", latency_ms=80.0)
    assert st.status == "HEALTHY"
    assert st.consecutive_failures == 0


def test_site_health_cli_command():
    result = runner.invoke(app, ["site-health"])
    assert result.exit_code == 0
    assert "JoBot Portal & ATS Site Health" in result.stdout
    assert "greenhouse" in result.stdout
    assert "ashby" in result.stdout
    assert "workable" in result.stdout
