"""Crash recovery, durable saga checkpoints, and idempotency tests."""

import json

import pytest

from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.asp.saga import ApplySaga, SagaStatus
from jobot.models.domain import JobPosting, PersonalInfo, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_recovery.db"
    return DatabaseManager(db_path=db_file)


@pytest.fixture
def test_profile() -> UserProfile:
    return UserProfile(
        profile_id="candidate_recovery_01",
        personal_info=PersonalInfo(
            first_name="Alex",
            last_name="Mercer",
            email="alex.mercer@example.com",
            phone="+14155552671",
            location_city="Seattle",
            location_country="USA",
        ),
        skills=["Python", "PostgreSQL", "Docker"],
    )


@pytest.fixture
def test_job() -> JobPosting:
    return JobPosting(
        job_id="job_recovery_01",
        site="greenhouse",
        url="https://boards.greenhouse.io/acme/jobs/101",
        title="Backend Engineer",
        company="Acme Corp",
        location="Remote",
        parsed_skills=["Python", "PostgreSQL"],
    )


def test_saga_checkpointing_and_resumption(temp_db: DatabaseManager):
    saga = ApplySaga.start(temp_db, "job_101", "candidate_01")
    assert saga.status == SagaStatus.RUNNING.value

    saga.checkpoint("tailoring", json.dumps({"summary": "Experienced Python Engineer"}))
    saga.checkpoint("grounding", "passed=True")

    steps = saga.steps()
    step_names = [s["step_name"] for s in steps]
    assert "tailoring" in step_names
    assert "grounding" in step_names

    # Resume from checkpoint
    resumed = ApplySaga.resume(temp_db, saga.saga_id)
    assert resumed is not None
    assert resumed.saga_id == saga.saga_id
    assert resumed.status == SagaStatus.RUNNING.value


@pytest.mark.asyncio
async def test_orchestrator_dry_run_produces_artifacts_and_completes_saga(
    temp_db: DatabaseManager,
    test_profile: UserProfile,
    test_job: JobPosting,
    tmp_path,
):
    orchestrator = ApplyOrchestrator(db=temp_db, artifact_dir=tmp_path / "resumes")
    result = orchestrator.apply(
        test_job,
        test_profile,
        dry_run=True,
    )
    res = await result
    assert res.dry_run is True
    assert res.artifacts.get("resume_pdf") is not None

    saga = ApplySaga.resume(temp_db, res.saga_id)
    assert saga is not None
    assert saga.status == SagaStatus.COMPLETED.value


def test_saga_compensation_on_failure(temp_db: DatabaseManager):
    saga = ApplySaga.start(temp_db, "job_failed_01", "candidate_01")
    saga.checkpoint("tailoring")
    saga.fail("submit", "Network socket timeout")

    steps_before_comp = saga.steps()
    assert any(s["step_name"] == "submit" and s["status"] == "FAILED" for s in steps_before_comp)

    saga.compensate("Quarantine application and reset form lock")
    assert saga.status == SagaStatus.COMPENSATED.value

    steps_after_comp = saga.steps()
    assert any(
        s["step_name"] == "submit" and s["status"] == "COMPENSATED" for s in steps_after_comp
    )
