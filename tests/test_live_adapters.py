"""Tests for Ashby and Workable Live Browser Form Filler Adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from jobot.adapters.ashby_live import AshbyLiveAdapter
from jobot.adapters.capabilities import AdapterCapability
from jobot.adapters.workable_live import WorkableLiveAdapter
from jobot.models.domain import Application, ApplicationStatus, JobPosting, PersonalInfo, UserProfile


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile(
        profile_id="test_user",
        personal_info=PersonalInfo(
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            phone="+14155550199",
            location_city="San Francisco",
            location_country="USA",
            linkedin_url="https://linkedin.com/in/janedoe",
            github_url="https://github.com/janedoe",
        ),
        skills=["Python", "FastAPI", "React", "PostgreSQL"],
    )


@pytest.fixture
def ashby_job() -> JobPosting:
    return JobPosting(
        job_id="ashby_123",
        site="ashby",
        url="https://jobs.ashbyhq.com/acme/123-456",
        title="Backend Engineer",
        company="Acme",
    )


@pytest.fixture
def workable_job() -> JobPosting:
    return JobPosting(
        job_id="workable_789",
        site="workable",
        url="https://apply.workable.com/techcorp/j/ABC123XYZ/",
        title="Software Engineer",
        company="TechCorp",
    )


@pytest.mark.asyncio
async def test_ashby_live_capabilities_and_parsing():
    adapter = AshbyLiveAdapter()
    assert adapter.capabilities == AdapterCapability.FULL_BROWSER

    posting = await adapter.parse_job_posting("https://jobs.ashbyhq.com/acme-corp/abcdef12-3456")
    assert posting.site == "ashby"
    assert posting.company == "Acme-corp"
    assert "abcdef12-3456" in posting.job_id


@pytest.mark.asyncio
async def test_ashby_live_fill_form(sample_profile, ashby_job):
    adapter = AshbyLiveAdapter()
    app = Application(application_id="app_ashby_1", job_id=ashby_job.job_id, site="ashby", idempotency_key="k_ashby_1")
    form_data = await adapter.fill_form(ashby_job, sample_profile, app)

    assert form_data["name"] == "Jane Doe"
    assert form_data["email"] == "jane.doe@example.com"
    assert form_data["phone"] == "+14155550199"
    assert form_data["linkedin"] == "https://linkedin.com/in/janedoe"
    assert app.form_values == form_data


@pytest.mark.asyncio
async def test_ashby_live_submit_blocked_without_env_flag(sample_profile, ashby_job, monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = AshbyLiveAdapter()
    app = Application(application_id="app_ashby_2", job_id=ashby_job.job_id, site="ashby", idempotency_key="k_ashby_2")
    await adapter.fill_form(ashby_job, sample_profile, app)

    ok = await adapter.submit_application(app)
    assert ok is False
    assert app.status is ApplicationStatus.BLOCKED
    assert "live browser runs disabled" in app.error_message


@pytest.mark.asyncio
async def test_ashby_live_submit_success_with_browser_mock(sample_profile, ashby_job, monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")

    mock_page = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body>Thank you for applying! Application submitted.</body></html>")

    locator_mock = AsyncMock()
    locator_mock.count = AsyncMock(return_value=1)
    mock_page.locator = MagicMock(return_value=locator_mock)

    mock_session = MagicMock()
    mock_session.page = mock_page

    adapter = AshbyLiveAdapter(browser_session=mock_session)
    app = Application(application_id="app_ashby_3", job_id=ashby_job.job_id, site="ashby", idempotency_key="k_ashby_3")
    await adapter.fill_form(ashby_job, sample_profile, app)

    ok = await adapter.submit_application(app)
    assert ok is True
    assert app.status is ApplicationStatus.SUBMITTED

    verification = await adapter.verify_submission(app)
    assert verification.success is True
    assert "ashby_" in verification.confirmation_id


@pytest.mark.asyncio
async def test_workable_live_capabilities_and_parsing():
    adapter = WorkableLiveAdapter()
    assert adapter.capabilities == AdapterCapability.FULL_BROWSER

    posting = await adapter.parse_job_posting("https://apply.workable.com/globex/j/998877/")
    assert posting.site == "workable"
    assert posting.company == "Globex"
    assert "998877" in posting.job_id


@pytest.mark.asyncio
async def test_workable_live_fill_form(sample_profile, workable_job):
    adapter = WorkableLiveAdapter()
    app = Application(application_id="app_workable_1", job_id=workable_job.job_id, site="workable", idempotency_key="k_workable_1")
    form_data = await adapter.fill_form(workable_job, sample_profile, app)

    assert form_data["firstname"] == "Jane"
    assert form_data["lastname"] == "Doe"
    assert form_data["email"] == "jane.doe@example.com"
    assert app.form_values == form_data


@pytest.mark.asyncio
async def test_workable_live_submit_success_with_browser_mock(sample_profile, workable_job, monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")

    mock_page = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.content = AsyncMock(return_value="<html><body>Application received! Successfully submitted.</body></html>")

    locator_mock = AsyncMock()
    locator_mock.count = AsyncMock(return_value=1)
    mock_page.locator = MagicMock(return_value=locator_mock)

    mock_session = MagicMock()
    mock_session.page = mock_page

    adapter = WorkableLiveAdapter(browser_session=mock_session)
    app = Application(application_id="app_workable_3", job_id=workable_job.job_id, site="workable", idempotency_key="k_workable_3")
    await adapter.fill_form(workable_job, sample_profile, app)

    ok = await adapter.submit_application(app)
    assert ok is True
    assert app.status is ApplicationStatus.SUBMITTED

    verification = await adapter.verify_submission(app)
    assert verification.success is True
    assert "workable_" in verification.confirmation_id
