"""Unit tests for DatabaseManager backup and restore (UC-44)."""

from pathlib import Path

from typer.testing import CliRunner

from jobot.cli.main import app
from jobot.models.domain import CandidateFact, TrustLevel
from jobot.storage.db import DatabaseManager

runner = CliRunner()


def test_db_backup_and_restore_roundtrip(tmp_path: Path):
    orig_db_path = tmp_path / "orig.db"
    backup_db_path = tmp_path / "backup.db"
    restored_db_path = tmp_path / "restored.db"

    db1 = DatabaseManager(orig_db_path)
    fact = CandidateFact(
        profile_id="test_p1",
        fact_type="contact",
        fact_key="primary_email",
        fact_value="aryan@example.com",
        trust_level=TrustLevel.TRUSTED,
    )
    db1.save_candidate_fact(fact)

    # Backup to backup_db_path
    db1.backup(backup_db_path)
    assert backup_db_path.exists()

    # Restore into fresh DB
    db2 = DatabaseManager(restored_db_path)
    db2.restore(backup_db_path)

    facts = db2.list_candidate_facts(profile_id="test_p1")
    assert len(facts) == 1
    assert facts[0].fact_value == "aryan@example.com"


def test_db_backup_and_restore_cli(tmp_path: Path):
    backup_file = tmp_path / "cli_backup.db"
    res_backup = runner.invoke(app, ["db", "backup", "--out", str(backup_file)])
    assert res_backup.exit_code == 0
    assert "Database backed up to" in res_backup.stdout
    assert backup_file.exists()

    res_restore = runner.invoke(app, ["db", "restore", str(backup_file)])
    assert res_restore.exit_code == 0
    assert "Database restored successfully" in res_restore.stdout
