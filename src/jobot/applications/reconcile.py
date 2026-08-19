"""H7 — Verification & Reconciliation harness (WS3, gap G3).

Trigger: an application in SUBMITTED, SUBMISSION_UNKNOWN, or
VERIFICATION_UNKNOWN.

Protocol (MASTER_PLAN_EXPANDED.md §12.5):
    1. FETCH   — adapter verify_submission only (NEVER submit_application)
    2. CLASSIFY— confirmed / unconfirmed / ambiguous
    3. EVIDENCE— capture verification proof
    4. TRANSITION — VERIFIED / stays-UNKNOWN / FAILED
    5. QUARANTINE — UNKNOWN after MAX_ATTEMPTS reconcile attempts

Key invariant: reconcile-never-replay. This service is structurally
incapable of re-executing a submission — it holds no code path to
submit_application, and the tests assert that even total verification
failure never produces a second submit call.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from jobot.adapters.base import SiteAdapter
from jobot.applications.state_machine import transition_application
from jobot.execution.engine import DurableTaskEngine, EffectStatus
from jobot.models.domain import Application, ApplicationStatus
from jobot.obs.alerts import AlertDispatcher, AlertLevel
from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)

MAX_RECONCILE_ATTEMPTS = 3

_RECONCILABLE = frozenset(
    {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_UNKNOWN,
        ApplicationStatus.VERIFICATION_UNKNOWN,
    }
)


class ReconciliationService:
    """Verify-only reconciliation over ambiguous application states."""

    def __init__(
        self,
        db: DatabaseManager,
        adapter: SiteAdapter,
        alert_dispatcher: AlertDispatcher | None = None,
        max_attempts: int = MAX_RECONCILE_ATTEMPTS,
    ) -> None:
        self.db = db
        self.adapter = adapter
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self.max_attempts = max_attempts
        self._engine = DurableTaskEngine(db)

    # ------------------------------------------------------------------

    def _attempts(self, app: Application) -> int:
        return int((app.form_values or {}).get("_reconcile_attempts", 0))

    def _bump_attempts(self, app: Application) -> int:
        if app.form_values is None:
            app.form_values = {}
        app.form_values["_reconcile_attempts"] = self._attempts(app) + 1
        return int(app.form_values["_reconcile_attempts"])

    async def reconcile(self, app: Application) -> Application:
        """Reconcile one application; returns the (possibly mutated) app."""
        if app.status not in _RECONCILABLE:
            return app

        try:
            result = await self._verify_only(app)
        except Exception as exc:  # network/adapter failure = ambiguous
            logger.warning("reconcile verify error for %s: %s", app.application_id[:8], exc)
            return self._record_ambiguous(app, f"verify error: {exc}")

        if getattr(result, "success", False):
            confirmation = str(getattr(result, "confirmation_id", "") or "")
            transition_application(app, ApplicationStatus.VERIFIED)
            # The effect ledger reflects the reconciled truth.
            effect = self._engine.get_effect(app.idempotency_key)
            if effect is not None and effect.status is not EffectStatus.COMMITTED:
                self._engine.update_effect(
                    app.idempotency_key,
                    EffectStatus.COMMITTED,
                    external_reference=confirmation or None,
                    task_id_for_events=f"asp_{app.application_id[:12]}",
                )
            self.db.save_application(app)
            self.alert_dispatcher.dispatch_alert(
                title="Application reconciled to VERIFIED",
                message=(
                    f"{app.site} application {app.application_id[:8]} reconciled "
                    f"without re-submission (confirmation={confirmation or 'n/a'})"
                ),
                level=AlertLevel.INFO,
            )
            return app

        reason = str(getattr(result, "reason", "") or "verification not confirmed")
        return self._record_ambiguous(app, reason)

    async def reconcile_all(self, limit: int = 100) -> list[Application]:
        """Reconcile every reconcilable application (scheduler entry point)."""
        out: list[Application] = []
        for app in self.db.list_applications(limit=limit):
            if app.status in _RECONCILABLE:
                out.append(await self.reconcile(app))
        return out

    # ------------------------------------------------------------------

    async def _verify_only(self, app: Application) -> Any:
        """FETCH step: the ONLY adapter interaction reconciliation performs.

        submit_application is deliberately unreachable from this service —
        reconcile-never-replay is structural, not conventional.
        """
        return await self.adapter.verify_submission(app)

    def _record_ambiguous(self, app: Application, reason: str) -> Application:
        attempts = self._bump_attempts(app)
        if attempts >= self.max_attempts:
            transition_application(
                app,
                ApplicationStatus.QUARANTINED,
                reason=f"unresolvable after {attempts} reconcile attempts: {reason}",
            )
            self.db.save_application(app)
            self.alert_dispatcher.dispatch_alert(
                title="Application QUARANTINED after failed reconciliation",
                message=(
                    f"{app.site} application {app.application_id[:8]} remained "
                    f"ambiguous after {attempts} verification attempts ({reason}); "
                    "manual investigation required"
                ),
                level=AlertLevel.HIGH,
            )
            return app
        app.error_message = f"reconcile attempt {attempts} ambiguous: {reason}"
        if app.status is ApplicationStatus.SUBMITTED:
            # Verification failed on an otherwise-confirmed submission.
            transition_application(
                app, ApplicationStatus.VERIFICATION_UNKNOWN, reason=app.error_message
            )
        else:
            app.updated_at = datetime.now(UTC)
        self.db.save_application(app)
        return app


__all__ = ["MAX_RECONCILE_ATTEMPTS", "ReconciliationService"]
