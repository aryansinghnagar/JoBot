"""Durable task execution engine (UC-01/02/03/05 — WS2, gate G2).

Replaces the in-memory `TaskGraphEngine` with a SQLite-backed engine that
survives process death at any point:

- **Atomic claiming**: a lease is acquired with a guarded UPDATE
  (`WHERE id = ? AND status = 'READY'`) inside `BEGIN IMMEDIATE`; two
  workers can never hold the same task.
- **Heartbeats + expiry reclaim**: workers heartbeat their lease; an
  expired lease returns the task to READY, and a task out of attempts is
  QUARANTINED — never silently retried forever.
- **Append-only event ledger**: every transition emits a `task_events` row
  with correlation/causation ids; the timeline of any task is replayable.
- **Effect ledger with idempotency**: an external side effect is reserved
  under a UNIQUE idempotency key before it runs; a duplicate reservation
  raises — a submitting worker that died mid-flight cannot cause a second
  submission (reconcile-never-replay: resolve UNKNOWN by verification, not
  re-execution).
- **Durable approvals**: ApprovalRequest rows survive restarts; decisions
  are guarded state transitions.
- **Checkpoints**: full harness state per (task, phase) for kill-anywhere
  resume.

All SQL is parameterized for values with fixed literal identifiers.
Timestamps are UTC ISO-8601 strings (lexicographically comparable).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from jobot.storage.db import DatabaseManager


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class EffectStatus(str, Enum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    COMPENSATED = "COMPENSATED"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    DEFERRED = "DEFERRED"
    EXPIRED = "EXPIRED"


# Legal task-state transitions (MASTER_PLAN_EXPANDED.md §3.4).
TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset({TaskStatus.CLAIMED, TaskStatus.CANCELLED, TaskStatus.WAITING}),
    TaskStatus.CLAIMED: frozenset({TaskStatus.RUNNING, TaskStatus.READY}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.WAITING,
            TaskStatus.VERIFYING,
            TaskStatus.RETRYING,
            TaskStatus.FAILED,
            TaskStatus.UNKNOWN,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.WAITING: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RETRYING: frozenset({TaskStatus.RUNNING, TaskStatus.QUARANTINED}),
    TaskStatus.VERIFYING: frozenset({TaskStatus.COMPLETED, TaskStatus.FAILED}),
    TaskStatus.FAILED: frozenset({TaskStatus.QUARANTINED, TaskStatus.RETRYING}),
    TaskStatus.QUARANTINED: frozenset(),
    TaskStatus.UNKNOWN: frozenset({TaskStatus.RUNNING, TaskStatus.QUARANTINED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


class EngineError(Exception):
    """Base class for durable-engine violations."""


class IllegalTransition(EngineError):
    """A requested state transition is not in the legal transition table."""


class DuplicateEffect(EngineError):
    """An effect with this idempotency key already exists (reserved/committed)."""


@dataclass
class DurableTask:
    id: str
    goal_id: str
    project_id: str
    description: str
    skill_tags: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = field(default_factory=list)
    owner: Optional[str] = None
    priority: int = 5
    risk_level: int = 0
    attempts: int = 0
    max_attempts: int = 3
    verification_plan: str = ""
    definition_of_done: str = ""
    evidence_paths: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class EffectRecord:
    id: str
    task_id: str
    effect_type: str
    idempotency_key: str
    request_hash: str
    status: EffectStatus
    application_id: Optional[str] = None
    external_reference: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ApprovalRecord:
    id: str
    task_id: str
    action_type: str
    risk_level: int
    requested_by: str
    status: ApprovalStatus
    application_id: Optional[str] = None
    requested_at: Optional[str] = None
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
    decision_reason: Optional[str] = None
    expires_at: Optional[str] = None


class DurableTaskEngine:
    """SQLite-backed task engine; safe across processes and restarts."""

    DEFAULT_LEASE_SECONDS = 300.0
    DEFAULT_APPROVAL_TTL_SECONDS = 7 * 24 * 3600.0

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Connection helper
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        """Yield a configured connection that is ALWAYS closed on exit.

        `with sqlite3.connect(...)` alone only manages transactions; on
        Windows an unclosed handle keeps the database file locked.
        """
        conn = sqlite3.connect(self.db.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Task lifecycle (UC-01)
    # ------------------------------------------------------------------

    def create_task(
        self,
        description: str,
        goal_id: str = "default",
        project_id: str = "default",
        *,
        depends_on: Optional[list[str]] = None,
        skill_tags: Optional[list[str]] = None,
        priority: int = 5,
        risk_level: int = 0,
        max_attempts: int = 3,
        verification_plan: str = "",
        definition_of_done: str = "",
        task_id: Optional[str] = None,
    ) -> DurableTask:
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        now = _iso(_now())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    id, goal_id, project_id, description, skill_tags, status,
                    depends_on, priority, risk_level, attempts, max_attempts,
                    verification_plan, definition_of_done, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    goal_id,
                    project_id,
                    description,
                    json.dumps(skill_tags or []),
                    json.dumps(depends_on or []),
                    priority,
                    risk_level,
                    max_attempts,
                    verification_plan,
                    definition_of_done,
                    now,
                    now,
                ),
            )
            conn.commit()
        self._append_event(task_id, "task_created", {"description": description})
        self.promote_ready()
        return self.get_task(task_id)  # type: ignore[return-value]

    def get_task(self, task_id: str) -> Optional[DurableTask]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[DurableTask]:
        with self._conn() as conn:
            if status is None:
                rows = conn.execute("SELECT * FROM tasks ORDER BY priority, created_at").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY priority, created_at",
                    (status.value,),
                ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: sqlite3.Row) -> DurableTask:
        return DurableTask(
            id=row["id"],
            goal_id=row["goal_id"],
            project_id=row["project_id"],
            description=row["description"],
            skill_tags=json.loads(row["skill_tags"]),
            status=TaskStatus(row["status"]),
            depends_on=json.loads(row["depends_on"]),
            owner=row["owner"],
            priority=row["priority"],
            risk_level=row["risk_level"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            verification_plan=row["verification_plan"],
            definition_of_done=row["definition_of_done"],
            evidence_paths=json.loads(row["evidence_paths"]),
            artifacts=json.loads(row["artifacts"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _set_status(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        new_status: TaskStatus,
        guarded_by: Optional[TaskStatus] = None,
    ) -> bool:
        """Guarded status update; returns False if the guard failed."""
        if guarded_by is None:
            cur = conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (new_status.value, _iso(_now()), task_id),
            )
        else:
            cur = conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
                (new_status.value, _iso(_now()), task_id, guarded_by.value),
            )
        return cur.rowcount == 1

    def transition(
        self,
        task_id: str,
        new_status: TaskStatus,
        *,
        actor: str = "system",
        payload: Optional[dict] = None,
    ) -> DurableTask:
        current = self.get_task(task_id)
        if current is None:
            raise EngineError(f"unknown task: {task_id}")
        if new_status not in TASK_TRANSITIONS[current.status]:
            raise IllegalTransition(
                f"illegal transition {current.status.value} -> {new_status.value} "
                f"for task {task_id}"
            )
        with self._conn() as conn:
            ok = self._set_status(conn, task_id, new_status, guarded_by=current.status)
            if not ok:
                raise IllegalTransition(
                    f"concurrent modification: task {task_id} left "
                    f"{current.status.value} before transition"
                )
            conn.commit()
        self._append_event(
            task_id,
            "task_transition",
            {"from": current.status.value, "to": new_status.value, **(payload or {})},
            actor=actor,
        )
        return self.get_task(task_id)  # type: ignore[return-value]

    def promote_ready(self) -> int:
        """PENDING tasks whose dependencies are all COMPLETED become READY."""
        promoted = 0
        now = _iso(_now())
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, depends_on FROM tasks WHERE status = 'PENDING'"
            ).fetchall()
            for row in rows:
                # Dependency membership is evaluated inside SQL via json_each
                # on the stored JSON array (fully parameterized).
                incomplete = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status != 'COMPLETED' "
                    "AND id IN (SELECT value FROM json_each(?))",
                    (row["depends_on"],),
                ).fetchone()[0]
                if incomplete == 0:
                    cur = conn.execute(
                        "UPDATE tasks SET status = 'READY', updated_at = ? WHERE id = ? "
                        "AND status = 'PENDING'",
                        (now, row["id"]),
                    )
                    promoted += cur.rowcount
            conn.commit()
        return promoted

    # ------------------------------------------------------------------
    # Atomic claiming, heartbeats, expiry reclaim (UC-01)
    # ------------------------------------------------------------------

    def claim_next(
        self, worker_id: str, lease_seconds: float = DEFAULT_LEASE_SECONDS
    ) -> Optional[DurableTask]:
        """Atomically lease the highest-priority READY task to a worker.

        The guarded UPDATE under BEGIN IMMEDIATE guarantees exactly one
        winner even with concurrent claimers (SQLite serializes writers).
        """
        now = _now()
        with self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT id FROM tasks WHERE status = 'READY' "
                "ORDER BY priority ASC, created_at ASC LIMIT 1"
            ).fetchone()
            if row is None:
                conn.rollback()
                return None
            task_id = row["id"]
            cur = conn.execute(
                "UPDATE tasks SET status = 'CLAIMED', owner = ?, updated_at = ? "
                "WHERE id = ? AND status = 'READY'",
                (worker_id, _iso(now), task_id),
            )
            if cur.rowcount != 1:  # unreachable under BEGIN IMMEDIATE; belt & braces
                conn.rollback()
                return None
            conn.execute(
                "INSERT INTO task_leases (task_id, worker_id, acquired_at, "
                "expires_at, heartbeat_at) VALUES (?, ?, ?, ?, ?)",
                (
                    task_id,
                    worker_id,
                    _iso(now),
                    _iso(now + timedelta(seconds=lease_seconds)),
                    _iso(now),
                ),
            )
            conn.execute(
                "INSERT INTO task_attempts (task_id, attempt_number, worker_id, started_at) "
                "VALUES (?, (SELECT COALESCE(MAX(attempt_number), 0) + 1 FROM task_attempts "
                "WHERE task_id = ?), ?, ?)",
                (task_id, task_id, worker_id, _iso(now)),
            )
            conn.commit()
        self._append_event(task_id, "task_claimed", {"worker_id": worker_id}, actor=worker_id)
        return self.get_task(task_id)

    def heartbeat(self, task_id: str, worker_id: str, extend_seconds: float = 60.0) -> bool:
        now = _now()
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE task_leases SET heartbeat_at = ?, expires_at = ? WHERE task_id = ? "
                "AND worker_id = ? AND expires_at > ?",
                (
                    _iso(now),
                    _iso(now + timedelta(seconds=extend_seconds)),
                    task_id,
                    worker_id,
                    _iso(now),
                ),
            )
            conn.commit()
            return cur.rowcount == 1

    def reclaim_expired(self, now: Optional[datetime] = None) -> list[str]:
        """Return expired-lease tasks to READY (or QUARANTINE at max attempts).

        Attempts are counted from task_attempts rows (one per claim); a task
        out of attempts is quarantined instead of retried.
        """
        now = now or _now()
        reclaimed: list[str] = []
        events: list[tuple[str, str, dict]] = []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT t.id, t.max_attempts, t.status FROM tasks t "
                "JOIN task_leases l ON l.task_id = t.id "
                "WHERE l.expires_at <= ? AND t.status IN ('CLAIMED', 'RUNNING', 'RETRYING')",
                (_iso(now),),
            ).fetchall()
            for row in rows:
                attempts = conn.execute(
                    "SELECT COUNT(*) FROM task_attempts WHERE task_id = ?",
                    (row["id"],),
                ).fetchone()[0]
                if attempts >= row["max_attempts"]:
                    cur = conn.execute(
                        "UPDATE tasks SET status = 'QUARANTINED', updated_at = ? "
                        "WHERE id = ? AND status IN ('CLAIMED', 'RUNNING', 'RETRYING')",
                        (_iso(now), row["id"]),
                    )
                    if cur.rowcount:
                        events.append(
                            (
                                row["id"],
                                "task_quarantined",
                                {"reason": "lease expired with no attempts left"},
                            )
                        )
                else:
                    cur = conn.execute(
                        "UPDATE tasks SET status = 'READY', updated_at = ? "
                        "WHERE id = ? AND status IN ('CLAIMED', 'RUNNING', 'RETRYING')",
                        (_iso(now), row["id"]),
                    )
                    if cur.rowcount:
                        events.append(
                            (
                                row["id"],
                                "lease_expired_reclaimed",
                                {"attempts_used": attempts},
                            )
                        )
                reclaimed.append(row["id"])
            conn.commit()
        # Event appends happen after the write transaction releases the lock
        # (each append uses its own connection — never nested writers).
        for task_id, event_type, payload in events:
            self._append_event(task_id, event_type, payload)
        return reclaimed

    # ------------------------------------------------------------------
    # Event ledger (UC-02)
    # ------------------------------------------------------------------

    def _append_event(
        self,
        task_id: str,
        event_type: str,
        payload: Optional[dict] = None,
        *,
        actor: str = "system",
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO task_events (task_id, event_type, payload, actor, "
                "correlation_id, causation_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    event_type,
                    json.dumps(payload or {}),
                    actor,
                    correlation_id,
                    causation_id,
                    _iso(_now()),
                ),
            )
            conn.commit()

    def append_event(
        self,
        task_id: str,
        event_type: str,
        payload: Optional[dict] = None,
        **kw: Any,
    ) -> None:
        """Public event-ledger append (UC-02)."""
        self._append_event(task_id, event_type, payload, **kw)

    def event_timeline(self, task_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY id",
                (task_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "event_type": r["event_type"],
                "payload": json.loads(r["payload"]),
                "actor": r["actor"],
                "correlation_id": r["correlation_id"],
                "causation_id": r["causation_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Effect ledger + idempotency (UC-03)
    # ------------------------------------------------------------------

    def reserve_effect(
        self,
        task_id: str,
        effect_type: str,
        idempotency_key: str,
        request_hash: str,
        application_id: Optional[str] = None,
    ) -> EffectRecord:
        """Reserve an external effect; duplicates raise DuplicateEffect.

        The UNIQUE idempotency key is the database-level guarantee: two
        workers racing to submit the same application cannot both reserve.
        The caller handles DuplicateEffect by reconciling the existing
        effect (verify, never re-execute).
        """
        effect_id = f"effect_{uuid.uuid4().hex[:12]}"
        now = _iso(_now())
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO external_effects (id, task_id, application_id, "
                    "effect_type, idempotency_key, request_hash, started_at, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')",
                    (
                        effect_id,
                        task_id,
                        application_id,
                        effect_type,
                        idempotency_key,
                        request_hash,
                        now,
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                existing = self.get_effect(idempotency_key)
                state = existing.status.value if existing else "UNKNOWN"
                raise DuplicateEffect(
                    f"effect with idempotency key {idempotency_key!r} already "
                    f"exists in state {state}"
                ) from exc
        self._append_event(
            task_id,
            "effect_reserved",
            {"effect_type": effect_type, "idempotency_key": idempotency_key},
        )
        rec = self.get_effect(idempotency_key)
        assert rec is not None
        return rec

    def get_effect(self, idempotency_key: str) -> Optional[EffectRecord]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM external_effects WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_effect(row)

    def _row_to_effect(self, row: sqlite3.Row) -> EffectRecord:
        return EffectRecord(
            id=row["id"],
            task_id=row["task_id"],
            effect_type=row["effect_type"],
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            status=EffectStatus(row["status"]),
            application_id=row["application_id"],
            external_reference=row["external_reference"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def update_effect(
        self,
        idempotency_key: str,
        status: EffectStatus,
        *,
        external_reference: Optional[str] = None,
        task_id_for_events: Optional[str] = None,
    ) -> Optional[EffectRecord]:
        """Effect-state update (e.g. PENDING/UNKNOWN -> COMMITTED/FAILED)."""
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE external_effects SET status = ?, completed_at = ?, "
                "external_reference = COALESCE(?, external_reference) "
                "WHERE idempotency_key = ? AND status != 'COMPENSATED'",
                (status.value, _iso(_now()), external_reference, idempotency_key),
            )
            conn.commit()
            if cur.rowcount != 1:
                return self.get_effect(idempotency_key)
        if task_id_for_events:
            self._append_event(
                task_id_for_events,
                "effect_updated",
                {"idempotency_key": idempotency_key, "status": status.value},
            )
        return self.get_effect(idempotency_key)

    # ------------------------------------------------------------------
    # Durable approvals (UC-05)
    # ------------------------------------------------------------------

    def create_approval(
        self,
        task_id: str,
        action_type: str,
        risk_level: int,
        requested_by: str = "system",
        application_id: Optional[str] = None,
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SECONDS,
    ) -> ApprovalRecord:
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        now = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO approval_requests (id, task_id, application_id, action_type, "
                "risk_level, requested_at, requested_by, status, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)",
                (
                    approval_id,
                    task_id,
                    application_id,
                    action_type,
                    risk_level,
                    _iso(now),
                    requested_by,
                    _iso(now + timedelta(seconds=ttl_seconds)),
                ),
            )
            conn.commit()
        self._append_event(
            task_id,
            "approval_requested",
            {"approval_id": approval_id, "action_type": action_type},
        )
        rec = self.get_approval(approval_id)
        assert rec is not None
        return rec

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approval_requests WHERE id = ?", (approval_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_approval(row)

    def _row_to_approval(self, row: sqlite3.Row) -> ApprovalRecord:
        return ApprovalRecord(
            id=row["id"],
            task_id=row["task_id"],
            action_type=row["action_type"],
            risk_level=row["risk_level"],
            requested_by=row["requested_by"],
            status=ApprovalStatus(row["status"]),
            application_id=row["application_id"],
            requested_at=row["requested_at"],
            decided_at=row["decided_at"],
            decided_by=row["decided_by"],
            decision_reason=row["decision_reason"],
            expires_at=row["expires_at"],
        )

    def list_approvals(
        self, status: ApprovalStatus = ApprovalStatus.PENDING
    ) -> list[ApprovalRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM approval_requests WHERE status = ? ORDER BY requested_at",
                (status.value,),
            ).fetchall()
        return [self._row_to_approval(r) for r in rows]

    def decide_approval(
        self,
        approval_id: str,
        decision: ApprovalStatus,
        decided_by: str = "human",
        reason: str = "",
    ) -> ApprovalRecord:
        """Guarded approval decision (PENDING -> APPROVED/DENIED/DEFERRED)."""
        if decision not in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.DENIED,
            ApprovalStatus.DEFERRED,
        ):
            raise EngineError(f"decision must be APPROVED/DENIED/DEFERRED, got {decision}")
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE approval_requests SET status = ?, decided_at = ?, decided_by = ?, "
                "decision_reason = ? WHERE id = ? AND status = 'PENDING'",
                (decision.value, _iso(_now()), decided_by, reason, approval_id),
            )
            conn.commit()
            if cur.rowcount != 1:
                raise EngineError(
                    f"approval {approval_id} is not PENDING (already decided or expired)"
                )
        rec = self.get_approval(approval_id)
        assert rec is not None
        self._append_event(
            rec.task_id,
            "approval_decided",
            {"approval_id": approval_id, "decision": decision.value, "by": decided_by},
            actor=decided_by,
        )
        return rec

    def expire_approvals(self, now: Optional[datetime] = None) -> int:
        now = now or _now()
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE approval_requests SET status = 'EXPIRED' "
                "WHERE status = 'PENDING' AND expires_at IS NOT NULL AND expires_at <= ?",
                (_iso(now),),
            )
            conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # Checkpoints (kill-anywhere resume)
    # ------------------------------------------------------------------

    def save_checkpoint(self, task_id: str, phase: str, state: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO checkpoints (task_id, phase, state_payload, created_at) "
                "VALUES (?, ?, ?, ?)",
                (task_id, phase, json.dumps(state), _iso(_now())),
            )
            conn.commit()
        self._append_event(task_id, "checkpoint_saved", {"phase": phase})

    def latest_checkpoint(self, task_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT phase, state_payload FROM checkpoints WHERE task_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        state = json.loads(row["state_payload"])
        state["_phase"] = row["phase"]
        with self._conn() as conn:
            conn.execute(
                "UPDATE checkpoints SET restored_at = ? WHERE task_id = ? AND id = ("
                "SELECT MAX(id) FROM checkpoints WHERE task_id = ?)",
                (_iso(_now()), task_id, task_id),
            )
            conn.commit()
        return state


__all__ = [
    "ApprovalRecord",
    "ApprovalStatus",
    "DurableTask",
    "DurableTaskEngine",
    "DuplicateEffect",
    "EffectRecord",
    "EffectStatus",
    "EngineError",
    "IllegalTransition",
    "TASK_TRANSITIONS",
    "TaskStatus",
]
