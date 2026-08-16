"""CLI tests for `jobot scrape` and `jobot dedup` (plan.md Phase 2)."""

import json

from typer.testing import CliRunner

from jobot.cli.main import app

runner = CliRunner()


def test_scrape_unknown_board_errors(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mystery_board"])
    assert res.exit_code == 1
    assert "Unknown board" in res.stdout


def test_scrape_mock_ats_table(tmp_path, monkeypatch, live_mock_ats_server):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mock_ats", "--limit", "5"])
    assert res.exit_code == 0
    assert "mock_ats" in res.stdout
    assert "Scraped Postings" in res.stdout
    assert "Total:" in res.stdout


def test_scrape_mock_ats_json(tmp_path, monkeypatch, live_mock_ats_server):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mock_ats", "--limit", "3", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["site"] == "mock_ats"
    assert data[0]["title"]
    assert data[0]["url"]


def test_scrape_no_dedup_flag(tmp_path, monkeypatch, live_mock_ats_server):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mock_ats", "--limit", "5", "--no-dedup"])
    assert res.exit_code == 0
    assert "duplicates 0" in res.stdout


def test_scrape_keeps_and_duplicates_stats(tmp_path, monkeypatch, live_mock_ats_server):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mock_ats", "--limit", "5"])
    assert "kept" in res.stdout
    assert "duplicates" in res.stdout


def test_dedup_stats_command(tmp_path, monkeypatch, live_mock_ats_server):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    res = runner.invoke(app, ["scrape", "mock_ats", "--limit", "2"])
    assert res.exit_code == 0
    res2 = runner.invoke(app, ["dedup", "--stats"])
    assert res2.exit_code == 0
    assert "Dedup cache" in res2.stdout