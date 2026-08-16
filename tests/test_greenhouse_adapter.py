import pytest
from jobot.adapters.greenhouse import GreenhouseAdapter
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile


@pytest.mark.asyncio
async def test_greenhouse_adapter_url_parsing():
    adapter = GreenhouseAdapter()
    board, job_id = adapter._extract_board_and_job_id("https://boards.greenhouse.io/acme/jobs/12345")

    assert board == "acme"
    assert job_id == "12345"


@pytest.mark.asyncio
async def test_greenhouse_adapter_parse_posting():
    adapter = GreenhouseAdapter()
    url = "https://boards.greenhouse.io/techcorp/jobs/999"
    job = await adapter.parse_job_posting(url)

    assert job.site == "greenhouse"
    assert job.job_id == "999"
    assert job.title != ""


@pytest.mark.asyncio
async def test_greenhouse_adapter_form_fill_and_submit(monkeypatch):
    adapter = GreenhouseAdapter()
    url = "https://boards.greenhouse.io/techcorp/jobs/999"
    job = await adapter.parse_job_posting(url)

    profile = UserProfile(
        profile_id="p_gh",
        personal_info=PersonalInfo(first_name="Aryan", email="gh@example.com"),
    )

    app = Application(
        application_id="app_gh",
        job_id=job.job_id,
        site="greenhouse",
        idempotency_key="key_gh",
        job_url=job.url,
    )

    filled = await adapter.fill_form(job, profile, app)
    assert filled["email"] == "gh@example.com"
    assert app.status == ApplicationStatus.FILLED

    # Mock HTTP 201 response for API POST submit
    class MockHTTPResponse:
        status = 201
        def __enter__(self): return self
        def __exit__(self, *args): pass

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5: MockHTTPResponse())

    submitted = await adapter.submit_application(app)
    assert submitted is True
    assert app.status == ApplicationStatus.SUBMITTED
