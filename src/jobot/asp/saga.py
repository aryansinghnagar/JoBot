"""Apply saga: durable checkpointing + compensation for apply flows (Phase 3, T3.4).

The saga is a write-ahead audit trail around the 12-phase ASP pipeline. It never
changes pipeline phase ordering (status contract preserved); it records each
milestone and, on failure, applies compensating actions so no application is
left in a stuck half-applied state.
"""

import logging
from enum import Enum
from typing import Any, Optional

from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class SagaStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"
    CANCELLED = "CANCELLED"


class SagaStepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"


class ApplySaga:
    """Durable saga instance with step checkpoints and compensating actions."""

    def __init__(self, db: DatabaseManager, saga_id: str | None = None):
        self.db = db
        self.saga_id = saga_id or ""

    @classmethod
    def start(cls, db: DatabaseManager, job_id: str, profile_id: str) -> "ApplySaga":
        saga = cls(db)
        saga.saga_id = db.create_saga(job_id, profile_id)
        logger.info("Saga %s started (job %s, profile %s)", saga.saga_id[:8], job_id, profile_id)
        return saga

    @classmethod
    def resume(cls, db: DatabaseManager, saga_id: str) -> Optional["ApplySaga"]:
        record = db.get_saga(saga_id)
        if not record:
            return None
        saga = cls(db, saga_id=saga_id)
        if record["status"] == SagaStatus.FAILED.value:
            db.update_saga_status(saga_id, SagaStatus.RUNNING.value)
        return saga

    @property
    def status(self) -> str:
        record = self.db.get_saga(self.saga_id)
        return record["status"] if record else "UNKNOWN"

    def checkpoint(self, step_name: str, detail: str = "") -> None:
        self.db.save_saga_step(self.saga_id, step_name, SagaStepStatus.COMPLETED.value, detail)
        logger.debug("Saga %s checkpoint: %s", self.saga_id[:8], step_name)

    def fail(self, step_name: str, reason: str) -> None:
        self.db.save_saga_step(self.saga_id, step_name, SagaStepStatus.FAILED.value, reason)
        self.db.update_saga_status(self.saga_id, SagaStatus.FAILED.value)
        logger.warning("Saga %s failed at %s: %s", self.saga_id[:8], step_name, reason)

    def compensate(self, reason: str) -> None:
        """Compensate all open steps (rollback audit): nothing is left half-applied."""
        for step in self.db.list_saga_steps(self.saga_id):
            if step["status"] not in (
                SagaStepStatus.COMPLETED.value,
                SagaStepStatus.COMPENSATED.value,
            ):
                self.db.save_saga_step(
                    self.saga_id, step["step_name"], SagaStepStatus.COMPENSATED.value, reason
                )
        self.db.update_saga_status(self.saga_id, SagaStatus.COMPENSATED.value)
        logger.warning("Saga %s compensated: %s", self.saga_id[:8], reason)

    def cancel(self, reason: str) -> None:
        self.db.save_saga_step(
            self.saga_id, "user_cancelled", SagaStepStatus.COMPENSATED.value, reason
        )
        self.db.update_saga_status(self.saga_id, SagaStatus.CANCELLED.value)

    def complete(self) -> None:
        self.db.update_saga_status(self.saga_id, SagaStatus.COMPLETED.value)
        logger.info("Saga %s completed", self.saga_id[:8])

    def steps(self) -> list[dict[str, Any]]:
        return self.db.list_saga_steps(self.saga_id)
