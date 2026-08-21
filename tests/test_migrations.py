"""Versioned-migration tests (UC-07): idempotency, tamper detection, status."""

import sqlite3

import pytest

from jobot.storage.db import DatabaseManager
from jobot.storage.migrations import (
    MIGRATIONS,
    MigrationError,
    migration_status,
    run_migrations,
)

WS2_TABLES = {
    "tasks",
    "task_attempts",
    "task_leases",
    "task_events",
    "task_artifacts",
    "task_dependencies",
    "external_effects",
    "approval_requests",
    "checkpoints",
    "incidents",
    "budget_reservations",
    "schema_migrations",
}


def _tables(path) -> set:
    conn = sqlite3.connect(path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def test_fresh_database_gets_all_ws2_tables(tmp_path):
    db = DatabaseManager(tmp_path / "fresh.db")
    tables = _tables(db.db_path)
    missing = WS2_TABLES - tables
    assert not missing, f"missing tables: {missing}"


def test_migrations_are_idempotent(tmp_path):
    db = DatabaseManager(tmp_path / "idem.db")
    with db._get_connection() as conn:  # noqa: SLF001
        first = run_migrations(conn)
        second = run_migrations(conn)
    assert first == [], "already applied by DatabaseManager init"
    assert second == []
    status = None
    with db._get_connection() as conn:  # noqa: SLF001
        status = migration_status(conn)
    assert status["applied"] == [m.version for m in MIGRATIONS]
    assert status["pending"] == []


def test_tampered_history_is_refused(tmp_path):
    db = DatabaseManager(tmp_path / "tamper.db")
    # Corrupt the recorded checksum of migration 1
    with db._get_connection() as conn:  # noqa: SLF001
        conn.execute("UPDATE schema_migrations SET checksum = 'deadbeef' WHERE version = 1")
        conn.commit()
    with db._get_connection() as conn:  # noqa: SLF001
        with pytest.raises(MigrationError):
            run_migrations(conn)


def test_legacy_database_upgrades(tmp_path):
    """A pre-WS2 database (old tasks table, no responded_at) upgrades cleanly."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE job_postings (job_id TEXT PRIMARY KEY, site TEXT NOT NULL,
            url TEXT NOT NULL, title TEXT NOT NULL, company TEXT NOT NULL,
            location TEXT, description TEXT, parsed_skills TEXT,
            discovered_at TEXT NOT NULL);
        CREATE TABLE applications (application_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL, site TEXT NOT NULL,
            profile_id TEXT NOT NULL DEFAULT 'default', status TEXT NOT NULL,
            idempotency_key TEXT UNIQUE NOT NULL,
            trust_level TEXT NOT NULL DEFAULT 'SUPERVISED',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE tasks (task_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL,
            title TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
        """
    )
    conn.commit()
    conn.close()

    db = DatabaseManager(path)
    tables = _tables(db.db_path)
    assert "schema_migrations" in tables
    assert "task_leases" in tables
    # legacy tasks table was replaced by the durable schema
    with db._get_connection() as conn:  # noqa: SLF001
        cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
    assert "definition_of_done" in cols
    assert "task_id" not in cols
