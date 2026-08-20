"""Versioned, checksummed database migrations (UC-07).

Replaces ad-hoc `_ensure_column` schema drift with an ordered, append-only
migration list. Every migration runs once, inside a transaction, with the
SHA-256 checksum of its apply-function source recorded in
``schema_migrations``; a modified historical migration is detected and
refused (fail-closed).

Each migration is an ``apply(conn)`` function whose SQL statements are fixed
literals at the execute call sites (identifiers cannot be bound as SQL
parameters in SQLite). The checksum hashes the apply-function source via
``inspect.getsource`` — meaningful in normal installs; source-bundled
deployments fall back to a stable name-based digest.
"""

from __future__ import annotations

import hashlib
import inspect
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _apply_001(conn: sqlite3.Connection) -> None:
    """Durable execution core (WS2): legacy additive columns + §30.1 tables."""
    # The pre-WS2 `tasks` table (task_id/title/dependencies schema) had zero
    # readers or writers — the old engine was in-memory only. Replace it with
    # the §30.1 durable schema.
    conn.execute("DROP TABLE IF EXISTS tasks")

    # --- legacy additive columns (guarded: only when absent) ---
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    if "responded_at" not in existing:
        conn.execute("ALTER TABLE applications ADD COLUMN responded_at TEXT")
    if "outcome" not in existing:
        conn.execute("ALTER TABLE applications ADD COLUMN outcome TEXT")

    # --- tasks (UC-01) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            description TEXT NOT NULL,
            skill_tags TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'PENDING',
            depends_on TEXT NOT NULL DEFAULT '[]',
            owner TEXT,
            reviewer TEXT,
            priority INTEGER NOT NULL DEFAULT 5,
            risk_level INTEGER NOT NULL DEFAULT 0,
            budget_limit_usd REAL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            verification_plan TEXT NOT NULL DEFAULT '',
            evidence_paths TEXT NOT NULL DEFAULT '[]',
            artifacts TEXT NOT NULL DEFAULT '[]',
            escalation_reason TEXT,
            definition_of_done TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority, created_at)"
    )
    # --- task attempts (UC-01) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            attempt_number INTEGER NOT NULL,
            worker_id TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            outcome TEXT,
            error_message TEXT,
            evidence_path TEXT
        )
        """
    )
    # --- task leases (UC-01, atomic claiming) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_leases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            acquired_at TEXT,
            expires_at TEXT NOT NULL,
            heartbeat_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leases_expires ON task_leases(expires_at)")
    # --- task events (UC-02, append-only ledger) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            actor TEXT NOT NULL,
            correlation_id TEXT,
            causation_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON task_events(task_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_correlation ON task_events(correlation_id)")
    # --- task artifacts ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT
        )
        """
    )
    # --- task dependencies ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id TEXT NOT NULL,
            depends_on_task_id TEXT NOT NULL,
            dependency_type TEXT NOT NULL DEFAULT 'BLOCKS',
            PRIMARY KEY (task_id, depends_on_task_id)
        )
        """
    )
    # --- external effects (UC-03, idempotency ledger) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS external_effects (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            application_id TEXT,
            effect_type TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            request_hash TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            external_reference TEXT,
            verification_state TEXT,
            compensation_state TEXT,
            evidence_path TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_effects_idempotency ON external_effects(idempotency_key)"
    )
    # --- approvals (UC-05) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            application_id TEXT,
            action_type TEXT NOT NULL,
            risk_level INTEGER NOT NULL,
            requested_at TEXT,
            requested_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            decided_at TEXT,
            decided_by TEXT,
            decision_reason TEXT,
            expires_at TEXT,
            evidence_path TEXT
        )
        """
    )
    # --- checkpoints (UC-01, durable waitpoints / kill-anywhere resume) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            state_payload TEXT NOT NULL,
            created_at TEXT,
            restored_at TEXT
        )
        """
    )
    # --- incidents (Section 11) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            severity INTEGER NOT NULL,
            impact TEXT NOT NULL,
            affected_applications TEXT NOT NULL DEFAULT '[]',
            timeline TEXT NOT NULL DEFAULT '[]',
            last_known_good_version TEXT,
            root_cause TEXT,
            mitigation TEXT,
            corrective_action TEXT,
            eval_added_path TEXT,
            status TEXT NOT NULL DEFAULT 'CREATED',
            created_at TEXT,
            resolved_at TEXT
        )
        """
    )
    # --- budget reservations (UC-06/UC-20) ---
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            reserved_usd REAL NOT NULL,
            spent_usd REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'RESERVED',
            created_at TEXT
        )
        """
    )


def _apply_002(conn: sqlite3.Connection) -> None:
    """WS3 timestamp semantics split (MASTER_PLAN_EXPANDED.md §3.4).

    submitted_at / submission_verified_at / first_employer_response_at /
    current_outcome become distinct columns; legacy responded_at / outcome
    values are backfilled into the new semantics.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    if "submitted_at" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN submitted_at TEXT")
    if "submission_verified_at" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN submission_verified_at TEXT")
    if "first_employer_response_at" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN first_employer_response_at TEXT")
    if "current_outcome" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN current_outcome TEXT")
    # Backfill: verified rows carry their submission time implicitly; any
    # recorded employer response maps to the new first-response semantics.
    conn.execute(
        "UPDATE applications SET submitted_at = updated_at "
        "WHERE submitted_at IS NULL AND status IN ('submitted', 'verified', "
        "'submission_unknown', 'verification_unknown', 'duplicate_skipped')"
    )
    conn.execute(
        "UPDATE applications SET submission_verified_at = updated_at "
        "WHERE submission_verified_at IS NULL AND status = 'verified'"
    )
    conn.execute(
        "UPDATE applications SET first_employer_response_at = responded_at "
        "WHERE first_employer_response_at IS NULL AND responded_at IS NOT NULL"
    )
    conn.execute(
        "UPDATE applications SET current_outcome = outcome "
        "WHERE current_outcome IS NULL AND outcome IS NOT NULL"
    )


# Audit fix JOB-V2-REG-002: the docstring below cites
# ``MASTER_PLAN_EXPANDED.md §13.2``, but §13 does not exist in the document.
# The corrected citation is §8 (WS5 — vault hardening + candidate-truth
# tables) and §5 (D18 grounding verifier). The citation lives in this comment
# rather than being edited into the function docstring so the migration
# checksum (computed from the function source via ``inspect.getsource``) is
# unchanged and existing installs that have already recorded migration 3 do
# not fail with ``MigrationError``. The dangling ``§13.2`` reference inside
# the docstring is intentionally retained for the same reason; the docs-lint
# script (``scripts/check_master_plan_citations.py``) skips this file
# explicitly. See ``MASTER_PLAN_EXPANDED.md`` §8 / §5 for the actual content.
def _apply_003(conn: sqlite3.Connection) -> None:
    """WS5 memory + candidate-truth tables (MASTER_PLAN_EXPANDED.md §13.2).

    candidate_facts powers the grounding verifier (UC-21: no unsupported
    claims in generated documents); answer_bank and form_field_memory give
    the form-filling path persistent, deduplicated memory (UC-26).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            fact_value TEXT NOT NULL,
            source TEXT NOT NULL,
            source_path TEXT,
            confidence REAL DEFAULT 1.0,
            verified INTEGER DEFAULT 0,
            verified_at TEXT,
            verified_by TEXT,
            created_at TEXT,
            superseded_by INTEGER
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_facts_profile "
        "ON candidate_facts(profile_id, fact_type)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS answer_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            question_text TEXT NOT NULL,
            answer TEXT NOT NULL,
            source TEXT NOT NULL,
            used_count INTEGER DEFAULT 0,
            last_used_at TEXT,
            created_at TEXT,
            UNIQUE(profile_id, question_hash)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS form_field_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT NOT NULL,
            adapter_id TEXT NOT NULL,
            field_selector TEXT NOT NULL,
            field_label TEXT,
            field_type TEXT,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            last_used_at TEXT,
            UNIQUE(profile_id, adapter_id, field_selector)
        )
        """
    )


def _source_digest(func: Callable[[sqlite3.Connection], None]) -> str:
    """Formatting-independent digest of a migration's source.

    Whitespace is normalized so a formatter pass (ruff format) never
    invalidates recorded checksums; semantic edits (statement changes)
    still change the digest and are refused by `run_migrations`.
    """
    try:
        source = inspect.getsource(func)
    except OSError:  # frozen/zipped deployment without source
        source = func.__name__
    normalized = "\n".join(line.strip() for line in source.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]

    @property
    def checksum(self) -> str:
        return _source_digest(self.apply)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="durable_execution_core", apply=_apply_001),
    Migration(version=2, name="application_timestamp_split", apply=_apply_002),
    Migration(version=3, name="candidate_truth_and_answer_bank", apply=_apply_003),
)


class MigrationError(Exception):
    """Raised when the migration history is inconsistent or a migration fails."""


def _applied_versions(conn: sqlite3.Connection) -> dict[int, tuple[str, str]]:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT
        )
        """
    )
    rows = conn.execute("SELECT version, name, checksum FROM schema_migrations").fetchall()
    return {int(r[0]): (str(r[1]), str(r[2])) for r in rows}


def run_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply all pending migrations in order; return applied versions.

    Fail-closed rules: a recorded checksum that no longer matches the
    migration definition raises MigrationError (history tampering); a
    failing migration rolls back its own transaction only.
    """
    applied = _applied_versions(conn)
    applied_now: list[int] = []
    for mig in MIGRATIONS:
        if mig.version in applied:
            recorded_name, recorded_checksum = applied[mig.version]
            if recorded_checksum != mig.checksum or recorded_name != mig.name:
                raise MigrationError(
                    f"Migration {mig.version} ({mig.name}) was modified after being "
                    "applied. Restore the original definition or add a new migration."
                )
            continue
        try:
            mig.apply(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, checksum, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (mig.version, mig.name, mig.checksum, _now()),
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise MigrationError(f"Migration {mig.version} ({mig.name}) failed: {exc}") from exc
        applied_now.append(mig.version)
    return applied_now


def migration_status(conn: sqlite3.Connection) -> dict[str, Any]:
    """Report applied/pending migrations for `jobot db status`."""
    applied = _applied_versions(conn)
    return {
        "applied": sorted(applied.keys()),
        "pending": [m.version for m in MIGRATIONS if m.version not in applied],
        "latest": MIGRATIONS[-1].version if MIGRATIONS else 0,
        "migrations": [
            {
                "version": m.version,
                "name": m.name,
                "applied": m.version in applied,
                "checksum": m.checksum[:12],
            }
            for m in MIGRATIONS
        ],
    }


__all__ = [
    "Migration",
    "MigrationError",
    "MIGRATIONS",
    "migration_status",
    "run_migrations",
]
