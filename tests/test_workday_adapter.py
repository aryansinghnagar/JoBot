"""Hermetic tests for the honest Workday adapter (cxs-API + live-browser gate).

Verifies: real cxs-API parsing/discovery (mocked), honest refusal to fabricate
submit/verify without a live browser, profile-grounded form fill, and the
Patchright submitter/verifier logic against a fake browser.
"""

import json
import urllib.error
import urllib.request

import pytest
from jobot.adapters.workday import WorkdayAdapter, WorkdaySubmitter, WorkdayVerifier
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile

WORKDAY_HOST = "https://toptal.wd3.myworkdayjobs.com/wday/cxs/toptal/Toptal"


class FakeHTTPResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


SINGLE_POSTING = {
    "jobPostingInfo": {
        "jobPostingTitle": "Senior Backend Engineer",
        "jobPostingId": "a1b2c3d4",
        "locationsText": "Remote",
        "externalUrl": "https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/Job_123",
        "jobDescription": "<p>Require Python &amp; PostgreSQL expertise.</p>",
    }
}

JOBS_PAYLOAD = {
    "total": 2,
    "jobPostings": [
        {
            "id": "Job_1",
            "title": "Engineer I",
            "externalPath": "/en-US/Toptal/job/Engineer-I_Job_1",
            "locationsText": "NYC",
        },
        {
            "id": "Job_2",
            "title": "Engineer II",
            "externalPath": "/en-US/Toptal/job/Engineer-II_Job_2",
            "locationsText": "SF",
        },
    ],
}


def _monkeypatch_post(monkeypatch, url_suffix: str, payload: dict):
    def fake_urlopen(req, timeout=5):
        if url_suffix not in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)
        assert req.get_method() == "POST"
        return FakeHTTPResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


class FakeLocator:
    def __init__(self, present: bool, text: str = ""):
        self._present = present
        self._text = text

    async def count(self):
        return 1 if self._present else 0

    @property
    def first(self):
        return self

    async def click(self):
        pass

    async def all_text_contents(self):
        return [self._text]

    async def inner_text(self):
        return self._text


class FakeBrowser:
    def __init__(
        self,
        body_text: str = "",
        apply_present: bool = False,
        submit_present: bool = False,
        guest_present: bool = False,
    ):
        self.body_text = body_text
        self.apply_present = apply_present
        self.submit_present = submit_present
        self.guest_present = guest_present
        self.goto_url = None

    async def goto(self, url, wait_until="domcontentloaded"):
        self.goto_url = url

    def locator(self, selector: str):
        if selector == "body":
            return FakeLocator(True, self.body_text)
        if "applyButton" in selector or "Apply" in selector:
            return FakeLocator(self.apply_present)
        if "submitButton" in selector or "Submit" in selector:
            return FakeLocator(self.submit_present)
        if "guest" in selector or "as guest" in selector:
            return FakeLocator(self.guest_present)
        return FakeLocator(False)


def _profile() -> UserProfile:
    return UserProfile(
        profile_id="p_wd",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Nagar",
            email="wd@example.com",
            phone="+919876543210",
            location_city="Bangalore",
        ),
    )


def _app(job_url: str) -> Application:
    return Application(
        application_id="app_wd",
        job_id="a1b2c3d4",
        site="workday",
        idempotency_key="key_wd",
        job_url=job_url,
    )


@pytest.mark.asyncio
async def test_workday_company_split():
    adapter = WorkdayAdapter()
    assert adapter.api._split_company("toptal") == ("toptal", "toptal")
    assert adapter.api._split_company("acme.acme") == ("acme", "acme")
    assert adapter.api._split_company("acme.othersite") == ("acme", "othersite")
    tenant, site = adapter.api._tenant_site_from_url(
        "https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/Job_123"
    )
    assert (tenant, site) == ("toptal", "Toptal")


@pytest.mark.asyncio
async def test_workday_parse_posting(monkeypatch):
    adapter = WorkdayAdapter()
    _monkeypatch_post(monkeypatch, "/jobPosting/a1b2c3d4", SINGLE_POSTING)
    job = await adapter.parse_job_posting(
        "https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4"
    )

    assert job.site == "workday"
    assert job.job_id == "a1b2c3d4"
    assert job.title == "Senior Backend Engineer"
    assert job.location == "Remote"
    assert "Python & PostgreSQL" in job.description


@pytest.mark.asyncio
async def test_workday_parse_posting_raises_on_fetch_error(monkeypatch):
    adapter = WorkdayAdapter()

    def boom(req, timeout=5):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    with pytest.raises(RuntimeError):
        await adapter.parse_job_posting(
            "https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/does-not-exist"
        )


@pytest.mark.asyncio
async def test_workday_discover_jobs(monkeypatch):
    adapter = WorkdayAdapter()
    _monkeypatch_post(monkeypatch, "/jobs", JOBS_PAYLOAD)

    postings = await adapter.discover_jobs(company="toptal", keywords="engineer", limit=2)

    assert len(postings) == 2
    assert postings[0].title == "Engineer I"
    assert postings[0].company == "toptal"
    assert "Job_2" in postings[1].url


@pytest.mark.asyncio
async def test_workday_discover_jobs_requires_company(monkeypatch):
    adapter = WorkdayAdapter()

    postings = await adapter.discover_jobs(keywords="engineer")

    assert postings == []


@pytest.mark.asyncio
async def test_workday_discover_jobs_empty_on_error(monkeypatch):
    adapter = WorkdayAdapter()

    def boom(req, timeout=5):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    postings = await adapter.discover_jobs(company="nope")

    assert postings == []


@pytest.mark.asyncio
async def test_workday_fill_form_is_profile_grounded():
    adapter = WorkdayAdapter()
    profile = _profile()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    filled = await adapter.fill_form(None, profile, app)  # type: ignore[arg-type]

    assert filled["email"] == "wd@example.com"
    assert filled["name"] == "Aryan Nagar"
    assert filled["address_city"] == "Bangalore"
    assert app.status == ApplicationStatus.FILLED


@pytest.mark.asyncio
async def test_workday_submit_refused_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = WorkdayAdapter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await adapter.submit_application(app)

    assert submitted is False
    assert app.status != ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_workday_verify_fails_honestly_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = WorkdayAdapter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    result = await adapter.verify_submission(app)

    assert result.success is False
    assert result.confidence == 0.0
    assert not result.confirmation_id


@pytest.mark.asyncio
async def test_workday_submitter_confirmation_observed():
    browser = FakeBrowser(body_text="Your application has been submitted. Thank you!")
    submitter = WorkdaySubmitter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await submitter.submit(app, page=browser)

    assert submitted is True
    assert app.status == ApplicationStatus.SUBMITTED
    assert browser.goto_url == app.job_url


@pytest.mark.asyncio
async def test_workday_submitter_full_flow():
    browser = FakeBrowser(
        body_text="Review your application. Your application has been submitted.",
        apply_present=True,
        guest_present=True,
        submit_present=True,
    )
    submitter = WorkdaySubmitter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await submitter.submit(app, page=browser)

    assert submitted is True
    assert app.status == ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_workday_submitter_no_confirmation_returns_false():
    browser = FakeBrowser(body_text="some intermediate page", apply_present=True, submit_present=True)
    submitter = WorkdaySubmitter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await submitter.submit(app, page=browser)

    assert submitted is False
    assert app.status != ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_workday_submitter_detects_already_applied():
    browser = FakeBrowser(body_text="You have already applied to this position.")
    submitter = WorkdaySubmitter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await submitter.submit(app, page=browser)

    assert submitted is False
    assert app.status == ApplicationStatus.DUPLICATE_SKIPPED


@pytest.mark.asyncio
async def test_workday_submitter_requires_page():
    submitter = WorkdaySubmitter()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    submitted = await submitter.submit(app, page=None)

    assert submitted is False


@pytest.mark.asyncio
async def test_workday_verifier_confirms_applied_state():
    browser = FakeBrowser(body_text="You have already applied to this position.")
    verifier = WorkdayVerifier()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    result = await verifier.verify(app, page=browser)

    assert result.success is True
    assert result.confidence >= 0.8
    assert result.confirmation_id == app.job_id


@pytest.mark.asyncio
async def test_workday_verifier_no_applied_state():
    browser = FakeBrowser(body_text="Job details. No application state shown.")
    verifier = WorkdayVerifier()
    app = _app("https://toptal.wd3.myworkdayjobs.com/en-US/Toptal/job/a1b2c3d4")

    result = await verifier.verify(app, page=browser)

    assert result.success is False
    assert result.confirmation_id is None