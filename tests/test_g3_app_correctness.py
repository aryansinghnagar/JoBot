"""Gate-G3 tests: application correctness under injected failure (WS3).

Proves the G3 criteria (MASTER_PLAN_EXPANDED.md §9.2):
- no duplicate submissions under ANY injected failure mode at submit time
- approvals are durable entities that survive restarts and gate submission
- ambiguous submissions reconcile (verify-only), never re-execute
- timestamp semantics survive the split (submitted / verified / response)
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.applications.reconcile import ReconciliationService
from jobot.applications.state_machine import (
    IllegalApplicationTransition,
    can_transition,
    transition_application,
)
from jobot.asp.pipeline import ApprovalRequiredError, ApplicationSubmissionPipeline
from jobot.execution.engine import ApprovalStatus, DurableTaskEngine, EffectStatus
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    PersonalInfo,
    UserProfile,
)
from jobot.obs.alerts import AlertDispatcher
from jobot.storage.db import DatabaseManager


class RecordingAdapter(MockATSAdapter):
    """Hermetic adapter: no HTTP; counts submits; injectable failures.

    submit_mode:
      "ok"      — submit succeeds
      "crash"   — the external submit REACHED the ATS, then the caller died
                  (models post-send crash: side effect happened, no receipt)
    verify_mode:
      "confirm" — verification succeeds with a confirmation id
      "deny"    — verification returns success=False
      "raise"   — verification raises (network down)
    """

    def __init__(self, submit_mode: str = "ok", verify_mode: str = "confirm") -> None:
        super().__init__(base_url="http://127.0.0.1:1")  # never contacted
        self.submit_mode = submit_mode
        self.verify_mode = verify_mode
        self.submit_calls = 0
        self.verify_calls = 0

    async def parse_job_posting(self, url: str) -> JobPosting:
        job_id = url.rstrip("/").split("/")[-1]
        return JobPosting(
            job_id=job_id,
            site="mock_ats",
            url=url,
            title="G3 Test Role",
            company="G3Corp",
            location="Remote",
            description="Resilient application protocol test.",
            parsed_skills=["Python"],
            discovered_at=datetime.now(timezone.utc),
        )

    async def submit_application(self, application: Application) -> bool:
        self.submit_calls += 1
        application.form_values["submission_id"] = f"sub_{self.submit_calls}"
        if self.submit_mode == "crash":
            raise ConnectionResetError("connection lost after send")
        return True

    async def verify_submission(self, application: Application):
        self.verify_calls += 1
        from jobot.models.domain import VerificationResult

        if self.verify_mode == "raise":
            raise TimeoutError("verify endpoint unreachable")
        if self.verify_mode == "deny":
            return VerificationResult(
                success=False, confidence=0.0, reason="ATS has no record (yet)"
            )
        return VerificationResult(
            success=True,
            confidence=1.0,
            confirmation_id=f"CONF_{(application.form_values or {}).get('submission_id', 'x')}",
            reason="receipt confirmed",
        )

    async def capture_screenshot(self) -> None:
        return None


def _profile() -> UserProfile:
    return UserProfile(
        profile_id="g3",
        personal_info=PersonalInfo(first_name="Gate", last_name="Three", email="g3@example.com"),
    )


def _pipeline(db, adapter, tmp_path) -> ApplicationSubmissionPipeline:
    return ApplicationSubmissionPipeline(adapter, db, Path(tmp_path) / "artifacts")


# ---------------------------------------------------------------------------
# State machine (§3.4 protocol)
# ---------------------------------------------------------------------------


def test_protocol_happy_chain_is_legal():
    app = Application(application_id="sm1", job_id="j", site="mock_ats", idempotency_key="k1")
    chain = [
        ApplicationStatus.PARSING,
        ApplicationStatus.PARSED,
        ApplicationStatus.MATCHING,
        ApplicationStatus.MATCHED,
        ApplicationStatus.FILLING,
        ApplicationStatus.FILLED,
        ApplicationStatus.REVIEWING,
        ApplicationStatus.REVIEWED,
        ApplicationStatus.PENDING_APPROVAL,
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.VERIFIED,
        ApplicationStatus.OUTCOME_TRACKING,
        ApplicationStatus.OFFER,
    ]
    for status in chain:
        transition_application(app, status)
    assert app.submitted_at is not None
    assert app.submission_verified_at is not None
    assert app.first_employer_response_at is not None
    assert app.current_outcome == "offer"


@pytest.mark.parametrize(
    ("frm", "to"),
    [
        (ApplicationStatus.INTENT, ApplicationStatus.SUBMITTED),  # skip pipeline
        (ApplicationStatus.REVIEWED, ApplicationStatus.SUBMITTING),  # no approval
        (ApplicationStatus.PENDING_APPROVAL, ApplicationStatus.SUBMITTED),  # skip submitting
        (ApplicationStatus.SUBMITTED, ApplicationStatus.SUBMITTING),  # backwards
        (ApplicationStatus.QUARANTINED, ApplicationStatus.SUBMITTING),  # terminal
        (ApplicationStatus.OFFER, ApplicationStatus.INTENT),  # terminal
    ],
)
def test_illegal_edges_rejected(frm, to):
    assert not can_transition(frm, to)
    app = Application(application_id="sm2", job_id="j", site="s", idempotency_key="k2", status=frm)
    with pytest.raises(IllegalApplicationTransition):
        transition_application(app, to)


def test_same_state_transition_is_idempotent():
    app = Application(
        application_id="sm3",
        job_id="j",
        site="s",
        idempotency_key="k3",
        status=ApplicationStatus.SUBMITTED,
    )
    transition_application(app, ApplicationStatus.SUBMITTED)  # adapters may pre-set status
    assert app.submitted_at is not None


def test_unknown_states_are_first_class():
    assert can_transition(ApplicationStatus.SUBMITTING, ApplicationStatus.SUBMISSION_UNKNOWN)
    assert can_transition(ApplicationStatus.SUBMISSION_UNKNOWN, ApplicationStatus.VERIFIED)
    assert can_transition(ApplicationStatus.SUBMISSION_UNKNOWN, ApplicationStatus.QUARANTINED)
    assert can_transition(ApplicationStatus.SUBMITTED, ApplicationStatus.VERIFICATION_UNKNOWN)
    assert can_transition(ApplicationStatus.VERIFICATION_UNKNOWN, ApplicationStatus.QUARANTINED)


# ---------------------------------------------------------------------------
# G3 centerpiece: duplicate submission impossible
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_duplicate_submission_when_worker_dies_after_send(tmp_path):
    """Crash AFTER the ATS received the application: the effect is UNKNOWN,
    the application is SUBMISSION_UNKNOWN, and NO code path — pipeline
    re-run, gated submit, or reconcile — ever calls submit_application a
    second time."""
    db = DatabaseManager(Path(tmp_path) / "g3a.db")
    adapter = RecordingAdapter(submit_mode="crash")

    app1 = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/42", _profile(), auto_approve=True
    )
    assert app1.status is ApplicationStatus.SUBMISSION_UNKNOWN
    assert adapter.submit_calls == 1

    engine = DurableTaskEngine(db)
    effect = engine.get_effect(app1.idempotency_key)
    assert effect is not None and effect.status is EffectStatus.UNKNOWN

    # A "new process" re-runs the pipeline for the same job: refused.
    app2 = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/42", _profile(), auto_approve=True
    )
    assert app2.status is ApplicationStatus.DUPLICATE_SKIPPED
    assert adapter.submit_calls == 1

    # The gated submit path also refuses to re-execute (DuplicateEffect ->
    # reconcile), and reconciliation verifies only.
    reconciler = ReconciliationService(
        db, adapter, alert_dispatcher=AlertDispatcher(Path(tmp_path) / "alerts.jsonl")
    )
    reconciled = await reconciler.reconcile(
        app2 if app2.status is not ApplicationStatus.DUPLICATE_SKIPPED else app1
    )
    assert reconciled.status is ApplicationStatus.VERIFIED
    assert adapter.submit_calls == 1, "reconciliation must never re-submit"
    assert adapter.verify_calls >= 1

    # The effect ledger reflects the reconciled truth.
    effect = DurableTaskEngine(db).get_effect(app1.idempotency_key)
    assert effect.status is EffectStatus.COMMITTED
    assert adapter.submit_calls == 1


@pytest.mark.asyncio
async def test_double_run_of_gated_submit_cannot_double_submit(tmp_path):
    """Two sequential gated submits after approval: the second finds the
    effect COMMITTED and reconciles forward without calling the adapter."""
    db = DatabaseManager(Path(tmp_path) / "g3b.db")
    adapter = RecordingAdapter(submit_mode="ok")

    pipeline = _pipeline(db, adapter, tmp_path)
    app = await pipeline.execute("https://mock.example/jobs/7", _profile(), auto_approve=True)
    assert app.status is ApplicationStatus.VERIFIED
    assert adapter.submit_calls == 1

    loaded = db.get_application_by_idempotency_key(app.idempotency_key)
    assert loaded is not None
    result = await _pipeline(db, adapter, tmp_path).submit_and_verify(loaded)
    # Autonomous app (auto_approve) passes the gate; the effect is already
    # COMMITTED so the adapter is never called again.
    assert adapter.submit_calls == 1
    assert result.status is ApplicationStatus.VERIFIED


# ---------------------------------------------------------------------------
# Durable approvals (G3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_waitpoint_survives_restart(tmp_path):
    db = DatabaseManager(Path(tmp_path) / "g3c.db")
    adapter = RecordingAdapter()

    app = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/9", _profile(), auto_approve=False
    )
    assert app.status is ApplicationStatus.PENDING_APPROVAL
    approval_id = app.form_values["_approval_id"]

    # Simulated restart: a fresh engine sees the PENDING approval.
    engine2 = DurableTaskEngine(db)
    pending = engine2.list_approvals(ApprovalStatus.PENDING)
    assert [a.id for a in pending] == [approval_id]

    # Gated submit before the decision is refused.
    loaded = db.get_application_by_idempotency_key(app.idempotency_key)
    assert loaded is not None
    with pytest.raises(ApprovalRequiredError):
        await _pipeline(db, adapter, tmp_path).submit_and_verify(loaded)
    assert adapter.submit_calls == 0

    # Decide (human, later, different process) -> submit proceeds.
    DurableTaskEngine(db).decide_approval(approval_id, ApprovalStatus.APPROVED, decided_by="human")
    result = await _pipeline(db, adapter, tmp_path).submit_and_verify(loaded)
    assert result.status is ApplicationStatus.VERIFIED
    assert adapter.submit_calls == 1


# ---------------------------------------------------------------------------
# H7 reconciliation harness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_submitted_success_verifies(tmp_path):
    db = DatabaseManager(Path(tmp_path) / "g3d.db")
    adapter = RecordingAdapter()
    app = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/11", _profile(), auto_approve=True
    )
    assert app.status is ApplicationStatus.VERIFIED  # already verified inline
    # reconciling a verified app is a no-op that never submits
    reconciled = await ReconciliationService(db, adapter).reconcile(app)
    assert reconciled.status is ApplicationStatus.VERIFIED
    assert adapter.submit_calls == 1


@pytest.mark.asyncio
async def test_reconcile_unknown_after_three_ambiguous_attempts_quarantines(tmp_path):
    db = DatabaseManager(Path(tmp_path) / "g3e.db")
    adapter = RecordingAdapter(submit_mode="crash", verify_mode="deny")
    alerts = Path(tmp_path) / "alerts.jsonl"

    app = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/13", _profile(), auto_approve=True
    )
    assert app.status is ApplicationStatus.SUBMISSION_UNKNOWN

    service = ReconciliationService(db, adapter, alert_dispatcher=AlertDispatcher(alerts))
    r1 = await service.reconcile(app)
    assert r1.status is ApplicationStatus.SUBMISSION_UNKNOWN  # stays, attempt counted
    r2 = await service.reconcile(r1)
    assert r2.status is ApplicationStatus.SUBMISSION_UNKNOWN
    r3 = await service.reconcile(r2)
    assert r3.status is ApplicationStatus.QUARANTINED
    assert adapter.submit_calls == 1, "never re-submitted across all reconcile attempts"
    assert adapter.verify_calls == 3
    assert alerts.exists()  # quarantine alert recorded


@pytest.mark.asyncio
async def test_reconcile_verify_exception_is_ambiguous_not_fatal(tmp_path):
    db = DatabaseManager(Path(tmp_path) / "g3f.db")
    adapter = RecordingAdapter(submit_mode="crash", verify_mode="raise")
    app = await _pipeline(db, adapter, tmp_path).execute(
        "https://mock.example/jobs/14", _profile(), auto_approve=True
    )
    assert app.status is ApplicationStatus.SUBMISSION_UNKNOWN
    reconciled = await ReconciliationService(
        db, adapter, alert_dispatcher=AlertDispatcher(Path(tmp_path) / "alerts.jsonl")
    ).reconcile(app)
    assert reconciled.status is ApplicationStatus.SUBMISSION_UNKNOWN
    assert adapter.submit_calls == 1


# ---------------------------------------------------------------------------
# Timestamp split persistence + migration backfill
# ---------------------------------------------------------------------------


def test_timestamp_split_roundtrip(tmp_path):
    db = DatabaseManager(Path(tmp_path) / "g3g.db")
    posting = JobPosting(
        job_id="ts-job",
        site="mock_ats",
        url="https://mock.example/jobs/99",
        title="TS Role",
        company="TSCorp",
        location="Remote",
        description="timestamp split roundtrip",
        discovered_at=datetime.now(timezone.utc),
    )
    db.save_job_posting(posting)
    app = Application(
        application_id="ts1",
        job_id="ts-job",
        site="mock_ats",
        idempotency_key="ts-key",
        status=ApplicationStatus.SUBMITTED,
    )
    transition_application(app, ApplicationStatus.SUBMITTED)
    db.save_application(app)
    loaded = db.get_application("ts1")
    assert loaded is not None
    assert loaded.submitted_at is not None
    assert loaded.submission_verified_at is None

    transition_application(loaded, ApplicationStatus.VERIFIED)
    db.save_application(loaded)
    reloaded = db.get_application("ts1")
    assert reloaded is not None
    assert reloaded.submission_verified_at is not None
    assert reloaded.submitted_at <= reloaded.submission_verified_at


def test_migration_v2_backfills_legacy_columns(tmp_path):
    import sqlite3

    from jobot.storage.migrations import migration_status

    path = tmp_path / "legacy2.db"
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
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            responded_at TEXT, outcome TEXT);
        INSERT INTO applications VALUES ('a1', 'j1', 'mock_ats', 'default',
            'verified', 'key-1', 'SUPERVISED', '2026-01-01T00:00:00+00:00',
            '2026-01-02T00:00:00+00:00', '2026-01-05T00:00:00+00:00', 'interview');
        """
    )
    conn.commit()
    conn.close()

    db = DatabaseManager(path)
    with db._get_connection() as conn:  # noqa: SLF001
        status = migration_status(conn)
        row = conn.execute(
            "SELECT submitted_at, submission_verified_at, first_employer_response_at, "
            "current_outcome FROM applications WHERE application_id = 'a1'"
        ).fetchone()
    assert 2 in status["applied"]
    assert row["submitted_at"] == "2026-01-02T00:00:00+00:00"  # backfilled from updated_at
    assert row["submission_verified_at"] == "2026-01-02T00:00:00+00:00"  # verified row
    assert row["first_employer_response_at"] == "2026-01-05T00:00:00+00:00"  # from responded_at
    assert row["current_outcome"] == "interview"  # from outcome
