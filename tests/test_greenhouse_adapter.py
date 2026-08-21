import json

import pytest

from jobot.adapters.greenhouse import GreenhouseAdapter
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile


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


SINGLE_JOB = {
    "id": 999,
    "title": "Senior Backend Engineer",
    "location": {"name": "Remote"},
    "content": "<p>Real job description from the board.</p>",
}

BOARD_JOBS = {
    "jobs": [
        {
            "id": 1,
            "title": "Engineer I",
            "location": {"name": "NYC"},
            "content": "job one",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
        },
        {
            "id": 2,
            "title": "Engineer II",
            "location": {"name": "SF"},
            "content": "job two",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
        },
    ]
}


def _monkeypatch_urlopen(monkeypatch, url_suffix: str, payload: dict):
    def fake_safe_urlopen(
        url, *, data=None, headers=None, timeout=10.0, method=None, allow_private_hosts=False
    ):
        if url_suffix not in url:
            raise FileNotFoundError(f"unexpected fetch: {url}")
        return FakeHTTPResponse(payload)

    monkeypatch.setattr("jobot.adapters.greenhouse.safe_urlopen", fake_safe_urlopen)


@pytest.mark.asyncio
async def test_greenhouse_adapter_url_parsing():
    adapter = GreenhouseAdapter()
    board, job_id = adapter._extract_board_and_job_id(
        "https://boards.greenhouse.io/acme/jobs/12345"
    )

    assert board == "acme"
    assert job_id == "12345"


@pytest.mark.asyncio
async def test_greenhouse_adapter_parse_posting(monkeypatch):
    adapter = GreenhouseAdapter()
    url = "https://boards.greenhouse.io/acme/jobs/999"
    _monkeypatch_urlopen(monkeypatch, "/jobs/999", SINGLE_JOB)
    job = await adapter.parse_job_posting(url)

    assert job.site == "greenhouse"
    assert job.job_id == "999"
    assert job.title == "Senior Backend Engineer"
    assert job.location == "Remote"
    assert job.description == "<p>Real job description from the board.</p>"


@pytest.mark.asyncio
async def test_greenhouse_adapter_parse_posting_raises_on_fetch_error(monkeypatch):
    adapter = GreenhouseAdapter()
    url = "https://boards.greenhouse.io/acme/jobs/404"

    def boom(*args, **kwargs):
        raise ConnectionError("simulated fetch failure")

    monkeypatch.setattr("jobot.adapters.greenhouse.safe_urlopen", boom)

    with pytest.raises(ConnectionError):
        await adapter.parse_job_posting(url)


@pytest.mark.asyncio
async def test_greenhouse_adapter_discover_jobs(monkeypatch):
    adapter = GreenhouseAdapter()
    _monkeypatch_urlopen(monkeypatch, "/jobs?content=true", BOARD_JOBS)

    postings = await adapter.discover_jobs(company="acme", limit=2)

    assert len(postings) == 2
    assert postings[0].title == "Engineer I"
    assert postings[0].company == "Acme"
    assert postings[1].url == "https://boards.greenhouse.io/acme/jobs/2"


@pytest.mark.asyncio
async def test_greenhouse_adapter_discover_jobs_empty_on_error(monkeypatch):
    adapter = GreenhouseAdapter()

    def boom(*args, **kwargs):
        raise ConnectionError("simulated fetch failure")

    monkeypatch.setattr("jobot.adapters.greenhouse.safe_urlopen", boom)

    postings = await adapter.discover_jobs(company="nope")

    assert postings == []


@pytest.mark.asyncio
async def test_greenhouse_adapter_form_fill_and_submit(monkeypatch):
    adapter = GreenhouseAdapter()
    _monkeypatch_urlopen(monkeypatch, "/jobs/999", SINGLE_JOB)
    url = "https://boards.greenhouse.io/acme/jobs/999"
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

    def fake_post(
        url, *, data=None, headers=None, timeout=10.0, method=None, allow_private_hosts=False
    ):
        assert method == "POST"
        assert "/applications" in url
        return FakeHTTPResponse({}, status=201)

    monkeypatch.setattr("jobot.adapters.greenhouse.safe_urlopen", fake_post)

    submitted = await adapter.submit_application(app)
    assert submitted is True
    assert app.status == ApplicationStatus.SUBMITTED
