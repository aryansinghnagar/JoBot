import json

from typer.testing import CliRunner

from jobot.cli.main import app
from jobot.models.domain import Application, ApplicationStatus, JobPosting, TrustLevel
from jobot.obs.alerts import AlertDispatcher, AlertLevel
from jobot.obs.tracing import TraceLogger
from jobot.storage.db import DatabaseManager

runner = CliRunner()


def test_cli_pause_and_resume_commands(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Test pause command
    pause_res = runner.invoke(app, ["pause"])
    assert pause_res.exit_code == 0
    assert "paused" in pause_res.stdout.lower()

    state_file = tmp_path / ".jobot" / "runner_state.json"
    assert state_file.exists()
    state_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert state_data["status"] == "PAUSED"

    # Test resume command
    resume_res = runner.invoke(app, ["resume"])
    assert resume_res.exit_code == 0
    assert "resumed" in resume_res.stdout.lower()
    resumed_data = json.loads(state_file.read_text(encoding="utf-8"))
    assert resumed_data["status"] == "RUNNING"


def test_cli_export_json_command(tmp_path):
    out_file = tmp_path / "export_test.json"
    res = runner.invoke(app, ["export", "--format", "json", "--output", str(out_file)])
    assert res.exit_code == 0
    assert out_file.exists()


def test_cli_schedule_list_command(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["schedule", "list"])
    assert res.exit_code == 0
    assert "schedules" in res.stdout.lower()


def test_cli_list_sites_command():
    res = runner.invoke(app, ["list-sites"])
    assert res.exit_code == 0
    assert "Supported Job Portals & ATS Adapters" in res.stdout
    assert "greenhouse" in res.stdout.lower()
    assert "lever" in res.stdout.lower()
    assert "workday" in res.stdout.lower()


def test_cli_site_health_command():
    res = runner.invoke(app, ["site-health"])
    assert res.exit_code == 0
    assert "Portal & ATS Site Health" in res.stdout
    assert "greenhouse" in res.stdout.lower()


def test_cli_status_command(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    db_path = tmp_path / "status_test.db"
    db = DatabaseManager(db_path)
    job = JobPosting(
        job_id="job_abc",
        site="greenhouse",
        url="https://boards.greenhouse.io/acme/jobs/123",
        title="Software Engineer",
        company="Acme Corp",
        location="Remote",
        description="Build software",
    )
    db.save_job_posting(job)
    app_record = Application(
        application_id="app_1234567890",
        job_id="job_abc",
        site="greenhouse",
        status=ApplicationStatus.VERIFIED,
        trust_level=TrustLevel.SUPERVISED,
        idempotency_key="idemp_123",
    )
    db.save_application(app_record)
    monkeypatch.setattr("jobot.cli.main.DatabaseManager", lambda *args, **kwargs: db)

    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0
    assert "Status" in res.stdout
    assert "greenhouse" in res.stdout


def test_cli_config_commands(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Show config
    show_res = runner.invoke(app, ["config", "show"])
    assert show_res.exit_code == 0
    assert "Configuration" in show_res.stdout

    # Set non-secret config
    set_res = runner.invoke(app, ["config", "set", "policy.max_daily_applications", "15"])
    assert set_res.exit_code == 0
    assert "stored" in set_res.stdout.lower()

    # Get config
    get_res = runner.invoke(app, ["config", "get", "policy.max_daily_applications"])
    assert get_res.exit_code == 0
    assert "15" in get_res.stdout

    # Unset config
    unset_res = runner.invoke(app, ["config", "unset", "policy.max_daily_applications"])
    assert unset_res.exit_code == 0
    assert "removed" in unset_res.stdout.lower()

    # Error on missing key
    err_res = runner.invoke(app, ["config", "get"])
    assert err_res.exit_code == 1

    # Error on unknown action
    unknown_res = runner.invoke(app, ["config", "invalid_action", "some_key"])
    assert unknown_res.exit_code == 1


def test_cli_traces_command(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    tl = TraceLogger(trace_dir=tmp_path / ".jobot" / "traces", run_id="test_run_123")
    monkeypatch.setattr("jobot.cli.main.TraceLogger", lambda *args, **kwargs: tl)

    # List when empty
    list_res = runner.invoke(app, ["traces", "list"])
    assert list_res.exit_code == 0
    assert "no trace files found" in list_res.stdout.lower()

    # Create a span and show trace
    span = tl.start_span("test_span")
    tl.end_span(span)

    list_res2 = runner.invoke(app, ["traces", "list"])
    assert list_res2.exit_code == 0
    assert "test_run_123" in list_res2.stdout

    show_res = runner.invoke(app, ["traces", "show", "test_run_123"])
    assert show_res.exit_code == 0
    assert "test_span" in show_res.stdout


def test_cli_alerts_command(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    dispatcher = AlertDispatcher(alert_file=tmp_path / ".jobot" / "alerts.json")
    monkeypatch.setattr("jobot.cli.main.AlertDispatcher", lambda *args, **kwargs: dispatcher)

    # List when empty
    empty_res = runner.invoke(app, ["alerts"])
    assert empty_res.exit_code == 0
    assert "no unacknowledged" in empty_res.stdout.lower()

    # Dispatch an alert and list
    dispatcher.dispatch_alert(
        level=AlertLevel.HIGH,
        title="Test Alert",
        message="Circuit breaker triggered on portal",
    )
    alerts = dispatcher.list_alerts()
    assert len(alerts) == 1
    alert_id = alerts[0]["alert_id"]

    list_res = runner.invoke(app, ["alerts"])
    assert list_res.exit_code == 0
    assert "Test Alert" in list_res.stdout

    # Acknowledge alert
    ack_res = runner.invoke(app, ["alerts", "--ack", alert_id])
    assert ack_res.exit_code == 0
    assert "acknowledged" in ack_res.stdout.lower()


def test_cli_evals_command():
    res = runner.invoke(app, ["evals"])
    assert res.exit_code == 0
    assert "Continuous Evaluation Results" in res.stdout
    assert "Pass Rate" in res.stdout


def test_cli_plugin_list_command():
    res = runner.invoke(app, ["plugin", "list"])
    assert res.exit_code == 0
    assert "plugins" in res.stdout.lower()


def test_cli_skill_gap_and_salary_commands(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    db = DatabaseManager(tmp_path / "analytics_test.db")
    monkeypatch.setattr("jobot.cli.main.DatabaseManager", lambda *args, **kwargs: db)

    # When profile is missing
    res_missing = runner.invoke(app, ["skill-gap"])
    assert res_missing.exit_code == 1
    assert "missing" in res_missing.stdout.lower()

    # When profile exists
    from jobot.models.domain import PersonalInfo, UserProfile
    from jobot.storage.vault import CredentialVault

    vault = CredentialVault()
    profile_dir = tmp_path / ".jobot" / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile = UserProfile(
        profile_id="default",
        personal_info=PersonalInfo(first_name="Test", last_name="User", email="test@example.com"),
        skills=["Python", "FastAPI"],
    )
    vault.save_encrypted_profile(profile, profile_dir / "default.enc")

    res_gap = runner.invoke(app, ["skill-gap"])
    assert res_gap.exit_code == 0
    assert "Skill Gap" in res_gap.stdout

    res_sal = runner.invoke(app, ["salary"])
    assert res_sal.exit_code == 0
    assert "Percentile" in res_sal.stdout or "Annual" in res_sal.stdout
