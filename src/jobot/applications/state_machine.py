"""Application protocol state machine (WS3, RF-5 — MASTER_PLAN_EXPANDED.md §3.4).

The application lifecycle is an explicit transition table, not free-form
enum mutation. `transition_application` is the single sanctioned way to move
an Application between statuses: it validates the edge, stamps the split
timestamps (submitted_at / submission_verified_at /
first_employer_response_at + current_outcome), and records the reason.

Protocol (mapped onto the existing ApplicationStatus vocabulary):

    intent -> parsing -> parsed -> matching -> matched -> filling -> filled
    -> reviewing -> reviewed -> pending_approval -> submitting
       -> submitted | submission_unknown
    submitted -> verified | verification_unknown
    submission_unknown -> verified | verification_unknown | quarantined
    verification_unknown -> verified | quarantined
    verified -> outcome_tracking -> interview | rejected | offer |
       withdrawn | expired

Cross-cutting edges (any non-terminal state): failed, cancelled, paused;
plus blocked / circuit_open / duplicate_skipped from their historical
entry points. Terminal states are frozen.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from jobot.models.domain import Application, ApplicationStatus

# Employer-response (outcome) states: entering one is an employer event.
_OUTCOME_STATES = frozenset(
    {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.EXPIRED,
    }
)

_TERMINAL = frozenset(
    {
        ApplicationStatus.QUARANTINED,
        ApplicationStatus.DUPLICATE_SKIPPED,
        ApplicationStatus.CANCELLED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.OFFER,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.EXPIRED,
    }
)

_CROSS_CUTTING_TARGETS = frozenset(
    {
        ApplicationStatus.FAILED,
        ApplicationStatus.CANCELLED,
        ApplicationStatus.PAUSED,
    }
)

_PROTOCOL_EDGES: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.INTENT: frozenset({ApplicationStatus.PARSING}),
    ApplicationStatus.PARSING: frozenset({ApplicationStatus.PARSED}),
    ApplicationStatus.PARSED: frozenset({ApplicationStatus.MATCHING}),
    ApplicationStatus.MATCHING: frozenset({ApplicationStatus.MATCHED, ApplicationStatus.REJECTED}),
    ApplicationStatus.MATCHED: frozenset({ApplicationStatus.FILLING}),
    ApplicationStatus.FILLING: frozenset({ApplicationStatus.FILLED}),
    ApplicationStatus.FILLED: frozenset({ApplicationStatus.REVIEWING}),
    ApplicationStatus.REVIEWING: frozenset({ApplicationStatus.REVIEWED}),
    ApplicationStatus.REVIEWED: frozenset(
        {ApplicationStatus.PENDING_APPROVAL, ApplicationStatus.BLOCKED}
    ),
    ApplicationStatus.PENDING_APPROVAL: frozenset(
        {ApplicationStatus.SUBMITTING, ApplicationStatus.BLOCKED}
    ),
    ApplicationStatus.SUBMITTING: frozenset(
        {
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.SUBMISSION_UNKNOWN,
            ApplicationStatus.CIRCUIT_OPEN,
        }
    ),
    ApplicationStatus.SUBMITTED: frozenset(
        {ApplicationStatus.VERIFIED, ApplicationStatus.VERIFICATION_UNKNOWN}
    ),
    ApplicationStatus.SUBMISSION_UNKNOWN: frozenset(
        {
            ApplicationStatus.VERIFIED,
            ApplicationStatus.VERIFICATION_UNKNOWN,
            ApplicationStatus.QUARANTINED,
        }
    ),
    ApplicationStatus.VERIFICATION_UNKNOWN: frozenset(
        {ApplicationStatus.VERIFIED, ApplicationStatus.QUARANTINED}
    ),
    ApplicationStatus.VERIFIED: frozenset(
        {ApplicationStatus.OUTCOME_TRACKING, ApplicationStatus.DUPLICATE_SKIPPED}
    ),
    ApplicationStatus.OUTCOME_TRACKING: frozenset(
        {
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.REJECTED,
            ApplicationStatus.OFFER,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.EXPIRED,
        }
    ),
    ApplicationStatus.INTERVIEW: frozenset({ApplicationStatus.OFFER, ApplicationStatus.REJECTED}),
    ApplicationStatus.OFFER: frozenset({ApplicationStatus.WITHDRAWN}),
    # Resumable intermediates
    ApplicationStatus.PAUSED: frozenset(
        {ApplicationStatus.SUBMITTING, ApplicationStatus.FAILED, ApplicationStatus.CANCELLED}
    ),
    ApplicationStatus.BLOCKED: frozenset(
        {ApplicationStatus.PENDING_APPROVAL, ApplicationStatus.CANCELLED}
    ),
    ApplicationStatus.CIRCUIT_OPEN: frozenset(
        {ApplicationStatus.SUBMITTING, ApplicationStatus.FAILED}
    ),
    # A failed run may be retried from the top (pipeline resets to INTENT).
    ApplicationStatus.FAILED: frozenset({ApplicationStatus.INTENT}),
    # Terminal states have no outgoing edges.
    ApplicationStatus.QUARANTINED: frozenset(),
    ApplicationStatus.DUPLICATE_SKIPPED: frozenset(),
    ApplicationStatus.CANCELLED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
    ApplicationStatus.EXPIRED: frozenset(),
}


class IllegalApplicationTransition(Exception):
    """The requested status change is not in the protocol transition table."""


def can_transition(current: ApplicationStatus, new: ApplicationStatus) -> bool:
    allowed: frozenset[ApplicationStatus] = _PROTOCOL_EDGES.get(current, frozenset())
    if current not in _TERMINAL:
        allowed = allowed | _CROSS_CUTTING_TARGETS
    return new in allowed


def transition_application(
    app: Application,
    new_status: ApplicationStatus,
    reason: Optional[str] = None,
) -> Application:
    """Validated status change with split-timestamp stamping.

    Raises IllegalApplicationTransition on illegal edges; on success mutates
    the application in place (status, timestamps, updated_at, error_message)
    and returns it. A no-change request (current == new) is an idempotent
    no-op — adapters may already have set the target status directly.
    """
    now = datetime.now(timezone.utc)
    if new_status is ApplicationStatus.SUBMITTED:
        app.submitted_at = app.submitted_at or now
    if new_status is ApplicationStatus.VERIFIED:
        app.submission_verified_at = app.submission_verified_at or now
    if new_status in _OUTCOME_STATES and app.first_employer_response_at is None:
        app.first_employer_response_at = now
        app.current_outcome = new_status.value
    if app.status is new_status:
        app.updated_at = now
        return app
    if not can_transition(app.status, new_status):
        raise IllegalApplicationTransition(
            f"illegal application transition {app.status.value} -> "
            f"{new_status.value} (application {app.application_id[:8]})"
        )
    app.status = new_status
    app.updated_at = now
    if reason is not None:
        app.error_message = reason
    return app


__all__ = [
    "IllegalApplicationTransition",
    "can_transition",
    "transition_application",
]
