"""Phase 3 T3.5: real Lever adapter (mocked urlopen) — parse, submit, honest verify."""

import json
import urllib.error
import urllib.request

import pytest
from jobot.adapters.lever import LeverAdapter
from jobot.models.domain import Application, PersonalInfo, UserProfile

LEVER_POSTING = {
    "id": "abc123",
    "text": "Senior Backend Engineer",
    "descriptionPlain": "Build Python services with FastAPI.",
    "categories": {"location": {"city": "Bangalore", "country": "IN", "full": "Bangalore, IN"}},
    "hostedUrl": "https://jobs.lever.co/acme/abc123",
    "lists": [{"text": "Python"}, {"text": "FastAPI"}],
}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _monkeypatch(monkeypatch, url_suffix, payload, status=200):
    def fake_urlopen(req, timeout=5):
        if url_suffix not in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)
        return FakeResponse(payload, status=status)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def _app():
    return Application(
        application_id="app_lever",
        job_id="abc123",
        site="lever",
        idempotency_key="k",
        job_url="https://jobs.lever.co/acme/abc123",
        form_values={"name": "Aryan Sharma", "email": "a@b.com", "phone": "+91"},
    )


@pytest.mark.asyncio
async def test_parse_real_lever_json(monkeypatch):
    adapter = LeverAdapter()
    _monkeypatch(monkeypatch, "/postings/acme/abc123", LEVER_POSTING)
    job = await adapter.parse_job_posting("https://jobs.lever.co/acme/abc123")

    assert job.job_id == "abc123"
    assert job.title == "Senior Backend Engineer"
    assert job.description == "Build Python services with FastAPI."
    assert job.location == "Bangalore, IN"
    assert job.parsed_skills == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_parse_raises_on_http_error(monkeypatch):
    adapter = LeverAdapter()

    def boom(req, timeout=5):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(urllib.error.HTTPError):
        await adapter.parse_job_posting("https://jobs.lever.co/acme/nope")


@pytest.mark.asyncio
async def test_submit_captures_confirmation(monkeypatch):
    adapter = LeverAdapter()
    _monkeypatch(monkeypatch, "/applications", {"id": "lev_app_1"}, status=200)
    app = _app()

    submitted = await adapter.submit_application(app)
    assert submitted is True
    assert app.status.value == "submitted"
    assert app.form_values["_lever_confirmation_id"] == "lev_app_1"


@pytest.mark.asyncio
async def test_verify_honest_without_confirmation():
    adapter = LeverAdapter()
    result = await adapter.verify_submission(_app())
    assert result.success is False
    assert "no confirmation" in result.reason.lower()


@pytest.mark.asyncio
async def test_verify_with_confirmation():
    adapter = LeverAdapter()
    app = _app()
    app.form_values["_lever_confirmation_id"] = "lev_app_1"
    result = await adapter.verify_submission(app)
    assert result.success is True
    assert result.confirmation_id == "lev_app_1"