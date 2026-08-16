"""Phase 3 T3.4: saga + orchestrator — dry-run, approval, dedup, compensation."""

import pytest
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.asp.saga import ApplySaga, SagaStatus
from jobot.models.domain import (
    CompensationDetails,
    Education,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)

DRAFT_JSON = (
    '{"summary": "Backend engineer building Python services.", '
    '"skills": ["Python", "FastAPI"], '
    '"experience": [{"company": "Mock Corp", "title": "Engineer", '
    '"bullets": ["Built APIs in Python."]}]}'
)


class FakeRouter:
    async def generate_text(
        self, prompt, system_prompt=None, fallback_chain=None, task=None, **kwargs
    ):
        if task == "resume_tailoring":
            return DRAFT_JSON
        if task == "resume_reviewer":
            return (
                '{"scores": {"accuracy": 5, "relevance": 5, "ats_friendliness": 5, '
                '"truthfulness": 5, "length": 5}, "issues": [], "verdict": "PASS"}'
            )
        return "I am excited about this role. Regards, Aryan."


def rich_profile(email: str = "aryan@example.com") -> UserProfile:
    return UserProfile(
        profile_id="p_saga",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Sharma",
            email=email,
            phone="+911234567890",
            location_city="Bangalore",
            location_country="India",
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI", "Django", "PostgreSQL"],
        experiences=[
            WorkExperience(
                title="Engineer",
                company="Mock Corp",
                start_date="2021",
                end_date="Present",
                description="Built REST APIs in Python with FastAPI and PostgreSQL.",
            ),
            WorkExperience(
                title="Developer",
                company="Old Co",
                start_date="2019",
                end_date="2021",
                description="Built Django features and wrote unit tests.",
            ),
        ],
        education=[
            Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)
        ],
    )


@pytest.mark.asyncio
async def test_saga_db_roundtrip(tmp_path):
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    saga = ApplySaga.start(db, "job1", "p1")
    saga.checkpoint("tailoring")
    saga.checkpoint("grounding")
    saga.complete()

    record = db.get_saga(saga.saga_id)
    assert record["status"] == SagaStatus.COMPLETED.value
    steps = db.list_saga_steps(saga.saga_id)
    assert [s["step_name"] for s in steps] == ["tailoring", "grounding"]
    assert db.list_sagas()[0]["saga_id"] == saga.saga_id


@pytest.mark.asyncio
async def test_saga_compensate_open_steps(tmp_path):
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    saga = ApplySaga.start(db, "job1", "p1")
    saga.checkpoint("tailoring")
    saga.fail("submit", "boom")
    saga.compensate("Submission failed: boom")

    steps = {s["step_name"]: s["status"] for s in db.list_saga_steps(saga.saga_id)}
    assert steps["tailoring"] == "COMPLETED"
    assert steps["submit"] == "COMPENSATED"
    assert db.get_saga(saga.saga_id)["status"] == SagaStatus.COMPENSATED.value


@pytest.mark.asyncio
async def test_dry_run_produces_artifacts(live_mock_ats_server, tmp_path):
    from jobot.adapters.mock_ats import MockATSAdapter
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    job = (await MockATSAdapter().discover_jobs(limit=1))[0]

    orchestrator = ApplyOrchestrator(db, router=FakeRouter(), artifact_dir=tmp_path / "resumes")
    result = await orchestrator.apply(job, rich_profile(), dry_run=True)

    assert result.dry_run is True
    assert result.app_status is None
    assert result.artifacts["ats_score"] >= 0.85
    assert result.artifacts["is_truthful"] is True
    assert "cover_letter" in result.artifacts
    assert db.get_saga(result.saga_id)["status"] == SagaStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_apply_supervised_approval_flow(live_mock_ats_server, tmp_path):
    from jobot.adapters.mock_ats import MockATSAdapter
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    job = (await MockATSAdapter().discover_jobs(limit=1))[0]
    orchestrator = ApplyOrchestrator(db, router=FakeRouter(), artifact_dir=tmp_path / "resumes")

    result = await orchestrator.apply(
        job, rich_profile(email="sup@example.com"), auto_approve=False
    )
    assert result.app_status == "pending_approval"
    assert result.application_id

    app = db.get_application(result.application_id)
    assert app.form_values.get("resume_path")

    final = await orchestrator.submit_approved(app)
    assert final.app_status == "verified"
    assert db.get_saga(result.saga_id)["status"] == SagaStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_apply_auto_approve_verified(live_mock_ats_server, tmp_path):
    from jobot.adapters.mock_ats import MockATSAdapter
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    job = (await MockATSAdapter().discover_jobs(limit=1))[0]
    orchestrator = ApplyOrchestrator(db, router=FakeRouter(), artifact_dir=tmp_path / "resumes")

    result = await orchestrator.apply(
        job, rich_profile(email="auto@example.com"), auto_approve=True
    )
    assert result.app_status == "verified"

    again = await orchestrator.apply(job, rich_profile(email="auto@example.com"), auto_approve=True)
    assert again.app_status == "duplicate_skipped"


@pytest.mark.asyncio
async def test_apply_compensation_on_parse_failure(live_mock_ats_server, tmp_path):
    from jobot.models.domain import JobPosting
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    bad_job = JobPosting(
        job_id="unreachable",
        site="mock_ats",
        url="http://127.0.0.1:1/jobs/nope",
        title="Nope",
        company="Nowhere",
    )
    orchestrator = ApplyOrchestrator(db, router=FakeRouter(), artifact_dir=tmp_path / "resumes")

    result = await orchestrator.apply(bad_job, rich_profile(), auto_approve=True)
    assert str(result.app_status).upper() in ("FAILED", "REJECTED")
    assert db.get_saga(result.saga_id)["status"] in (
        SagaStatus.FAILED.value,
        SagaStatus.COMPENSATED.value,
    )


@pytest.mark.asyncio
async def test_apply_unknown_resume_saga(tmp_path):
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(db_path=tmp_path / "test.db")
    orchestrator = ApplyOrchestrator(db, router=FakeRouter(), artifact_dir=tmp_path / "resumes")
    from jobot.models.domain import JobPosting

    job = JobPosting(job_id="j", site="mock_ats", url="http://x/j", title="t", company="c")
    result = await orchestrator.apply(job, rich_profile(), resume_saga_id="missing")
    assert result.notes == ["Saga 'missing' not found"]
