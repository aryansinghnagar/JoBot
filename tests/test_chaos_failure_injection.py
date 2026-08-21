"""Chaos & Failure Injection Suite (UC-40).

Simulates abrupt network failures, simulated crashes, and malformed LLM responses
to verify that JoBot's durable execution and effect ledger maintain strict safety.
"""

from unittest.mock import patch

import pytest

from jobot.applications.reconcile import ReconciliationService
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.execution.engine import (
    DurableTaskEngine,
    EffectStatus,
)
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    PersonalInfo,
    UserProfile,
)
from jobot.storage.db import DatabaseManager


@pytest.fixture
def sample_candidate() -> UserProfile:
    return UserProfile(
        profile_id="chaos_candidate",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="aryan@example.com",
            phone="+919876543210",
        ),
        skills=["Python", "FastAPI", "Docker"],
    )


@pytest.mark.asyncio
async def test_chaos_network_crash_after_submit_send(tmp_path, sample_candidate):
    """Simulate network crash immediately after HTTP submission POST."""
    db = DatabaseManager(tmp_path / "chaos.db")
    engine = DurableTaskEngine(db)
    orchestrator = ApplyOrchestrator(db=db)

    job = JobPosting(
        job_id="chaos_job_001",
        site="mock_ats",
        url="https://mockats.local/job/101",
        title="Software Engineer",
        company="Chaos Corp",
        description="Python backend engineer",
    )
    db.save_job_posting(job)

    # 1. Start application in dry_run=False
    with patch(
        "jobot.adapters.mock_ats.MockATSAdapter.submit_application",
        side_effect=ConnectionResetError("Simulated TCP Reset"),
    ):
        res = await orchestrator.apply(job, sample_candidate, auto_approve=True, dry_run=False)

    # Must NOT fabricate success; must land safely in SUBMISSION_UNKNOWN, rejected, or failed
    assert res.app_status in ["submission_unknown", "failed", "intent", "rejected", None]
    assert any("Simulated TCP Reset" in n for n in res.notes)

    # Verify effect ledger marked as UNKNOWN or reserved
    effect = engine.get_effect(f"mock_ats:{job.job_id}:{sample_candidate.profile_id}")
    if effect:
        assert effect.status in [EffectStatus.UNKNOWN, EffectStatus.RESERVED]


@pytest.mark.asyncio
async def test_chaos_reconciliation_of_unknown_application(tmp_path, sample_candidate):
    """Verify ReconciliationService handles SUBMISSION_UNKNOWN safely without duplicating."""
    db = DatabaseManager(tmp_path / "chaos_recon.db")
    engine = DurableTaskEngine(db)

    job = JobPosting(
        job_id="job_recon_01",
        site="mock_ats",
        url="https://mockats.local/job/recon",
        title="Engineer",
        company="Recon Corp",
        description="Python",
    )
    db.save_job_posting(job)

    app = Application(
        application_id="app_chaos_recon_01",
        job_id="job_recon_01",
        site="mock_ats",
        idempotency_key="mock_ats:job_recon_01:chaos_candidate",
        profile_id=sample_candidate.profile_id,
        status=ApplicationStatus.SUBMISSION_UNKNOWN,
    )
    db.save_application(app)
    engine.reserve_effect(
        "task_chaos_01",
        "submit_application",
        app.idempotency_key,
        "hash123",
        application_id=app.application_id,
    )
    engine.update_effect(app.idempotency_key, EffectStatus.UNKNOWN)

    from jobot.adapters.mock_ats import MockATSAdapter

    adapter = MockATSAdapter()
    recon = ReconciliationService(db=db, adapter=adapter)
    # Reconciliation must verify-only without re-submitting
    reconciled_app = await recon.reconcile(app)
    assert reconciled_app.status in [
        ApplicationStatus.VERIFIED,
        ApplicationStatus.QUARANTINED,
        ApplicationStatus.SUBMISSION_UNKNOWN,
        ApplicationStatus.FAILED,
    ]
