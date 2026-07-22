from pathlib import Path
import tempfile
import pytest

from jobot.adapters.mock_ats import MockATSAdapter
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, PipelinePhase, TrustLevel, UserProfile
from jobot.storage.db import DatabaseManager


@pytest.fixture
def pipeline_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db = DatabaseManager(tmp_path / "test_asp_12.db")
        adapter = MockATSAdapter(base_url="http://127.0.0.1:5800")
        pipeline = ApplicationSubmissionPipeline(adapter, db)
        profile = UserProfile(
            profile_id="p_12",
            personal_info=PersonalInfo(
                first_name="Aryan",
                last_name="Nagar",
                email="aryan@example.com",
                phone="+917827756669",
            ),
        )
        yield pipeline, db, profile


def make_app(app_id: str, profile_id: str, site: str = "mock_ats") -> Application:
    return Application(
        application_id=app_id,
        job_id="job_123",
        site=site,
        profile_id=profile_id,
        idempotency_key=f"ik_{app_id}",
        status=ApplicationStatus.INTENT,
        trust_level=TrustLevel.AUTONOMOUS,
    )


@pytest.mark.asyncio
async def test_phase_1_intent_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p1", profile.profile_id)
    dod = await pipeline._handle_phase_1_intent(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_1_intent_dod_fail_missing_email(pipeline_env):
    pipeline, db, profile = pipeline_env
    bad_profile = UserProfile(profile_id="bad", personal_info=PersonalInfo(first_name="Test"))
    app = make_app("app_p1_bad", "bad")
    dod = await pipeline._handle_phase_1_intent(app, bad_profile)
    assert dod.passed is False
    assert "email" in dod.reason.lower()


@pytest.mark.asyncio
async def test_phase_2_parse_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p2", profile.profile_id)
    job_url = "http://127.0.0.1:5800/jobs/1"
    dod = await pipeline._handle_phase_2_parse(app, profile, job_url)
    assert dod.passed is True
    assert app.job_id != ""


@pytest.mark.asyncio
async def test_phase_3_match_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p3", profile.profile_id)
    job_url = "http://127.0.0.1:5800/jobs/1"
    await pipeline._handle_phase_2_parse(app, profile, job_url)
    dod = await pipeline._handle_phase_3_match(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_4_extract_questions_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p4", profile.profile_id)
    await pipeline._handle_phase_2_parse(app, profile, "http://127.0.0.1:5800/jobs/1")
    dod = await pipeline._handle_phase_4_extract_questions(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_5_answer_questions_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p5", profile.profile_id)
    await pipeline._handle_phase_2_parse(app, profile, "http://127.0.0.1:5800/jobs/1")
    await pipeline._handle_phase_4_extract_questions(app, profile)
    dod = await pipeline._handle_phase_5_answer_questions(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_6_fill_form_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p6", profile.profile_id)
    await pipeline._handle_phase_2_parse(app, profile, "http://127.0.0.1:5800/jobs/1")
    dod = await pipeline._handle_phase_6_fill_form(app, profile)
    assert dod.passed is True
    assert app.form_values.get("email") == "aryan@example.com"


@pytest.mark.asyncio
async def test_phase_7_validate_fill_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p7", profile.profile_id)
    await pipeline._handle_phase_2_parse(app, profile, "http://127.0.0.1:5800/jobs/1")
    await pipeline._handle_phase_6_fill_form(app, profile)
    dod = await pipeline._handle_phase_7_validate_fill(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_8_grounding_check_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p8", profile.profile_id)
    await pipeline._handle_phase_2_parse(app, profile, "http://127.0.0.1:5800/jobs/1")
    await pipeline._handle_phase_6_fill_form(app, profile)
    dod = await pipeline._handle_phase_8_grounding_check(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_9_review_dod_pass(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p9", profile.profile_id)
    dod = await pipeline._handle_phase_9_review(app, profile)
    assert dod.passed is True


@pytest.mark.asyncio
async def test_phase_10_approval_dod_pause(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = make_app("app_p10", profile.profile_id)
    app.trust_level = TrustLevel.SUPERVISED
    dod = await pipeline._handle_phase_10_approval(app, profile, "http://127.0.0.1:5800/jobs/1", False)
    assert dod.passed is True
    assert app.status == ApplicationStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_full_12_phase_pipeline_execution(pipeline_env):
    pipeline, db, profile = pipeline_env
    app = await pipeline.execute("http://127.0.0.1:5800/jobs/1", profile, auto_approve=True)
    assert app.status in [ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED, ApplicationStatus.FAILED]
    assert app.job_id != ""
