import json
import pytest
from typer.testing import CliRunner
from jobot.cli.main import app

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
