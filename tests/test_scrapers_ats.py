"""Direct-API ATS family adapter tests (lever / ashby / smartrecruiters mappers)."""

import asyncio
import json
import urllib.request

import pytest

from jobot.scrapers.ats import (
    ATS_FAMILY_BOARDS,
    AshbyAdapter,
    LeverAdapter,
    SmartRecruitersAdapter,
    _fetch_json,
    _strip_html,
)


def test_strip_html():
    assert _strip_html("<p>Hello <b>World</b></p>") == "Hello World"
    assert _strip_html("&amp;") == "&"


def test_ats_family_boards():
    assert set(ATS_FAMILY_BOARDS) == {"lever", "ashby", "smartrecruiters"}


@pytest.mark.asyncio
async def test_lever_map_modern_schema():
    adapter = LeverAdapter()
    payload = [
        {
            "id": "abc-123",
            "text": "Senior Backend Engineer",
            "categories": {"location": "Berlin, Germany"},
            "hostedUrl": "https://jobs.lever.co/acme/abc-123",
            "descriptionPlain": "Build the platform.",
        },
        {"id": "def-456", "text": ""},  # no title -> skipped
    ]
    postings = adapter._map("acme", payload, limit=10)

    assert len(postings) == 1
    p = postings[0]
    assert p.job_id == "lever:acme:abc-123"
    assert p.title == "Senior Backend Engineer"
    assert p.location == "Berlin, Germany"
    assert p.url == "https://jobs.lever.co/acme/abc-123"
    assert p.description == "Build the platform."


@pytest.mark.asyncio
async def test_lever_map_html_fallback():
    adapter = LeverAdapter()
    payload = [{"id": "x", "text": "Engineer", "description": "<p>Hello <b>there</b></p>"}]
    postings = adapter._map("acme", payload, limit=10)

    assert postings[0].description == "Hello there"


@pytest.mark.asyncio
async def test_ashby_map_location_dict_or_str():
    adapter = AshbyAdapter()
    payload = {
        "jobs": [
            {
                "title": "Product Designer",
                "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                "location": {"name": "San Francisco, CA"},
                "descriptionHtml": "<p>Design things</p>",
            },
            {
                "title": "Data Analyst",
                "jobUrl": "https://jobs.ashbyhq.com/acme/2",
                "location": "Remote",
            },
        ]
    }
    postings = adapter._map("acme", payload, limit=10)

    assert len(postings) == 2
    assert postings[0].location == "San Francisco, CA"
    assert postings[1].location == "Remote"
    assert postings[0].description == "Design things"


@pytest.mark.asyncio
async def test_ashby_map_non_dict_payload_empty():
    adapter = AshbyAdapter()
    assert adapter._map("acme", [], limit=10) == []
    assert adapter._map("acme", {"jobs": None}, limit=10) == []


@pytest.mark.asyncio
async def test_smartrecruiters_map():
    adapter = SmartRecruitersAdapter()
    payload = {
        "content": [
            {
                "name": "Software Engineer",
                "ref": "12345",
                "location": {"city": "Amsterdam", "country": "NL"},
                "jobAd": {
                    "sections": {
                        "jobDescription": {"text": "Write code and ship."},
                    }
                },
            }
        ]
    }
    postings = adapter._map("adidas", payload, limit=10)

    assert len(postings) == 1
    p = postings[0]
    assert p.title == "Software Engineer"
    assert p.location == "Amsterdam, NL"
    assert p.url == "https://jobs.smartrecruiters.com/adidas/12345"
    assert p.description == "Write code and ship."


@pytest.mark.asyncio
async def test_discover_jobs_empty_without_company():
    adapter = LeverAdapter()
    assert await adapter.discover_jobs() == []


@pytest.mark.asyncio
async def test_discover_jobs_empty_on_fetch_error(monkeypatch):
    adapter = LeverAdapter(company="acme")

    def boom(url: str, timeout_s: float = 10.0):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr("jobot.scrapers.ats._fetch_json", boom)

    assert await adapter.discover_jobs() == []


@pytest.mark.asyncio
async def test_discover_jobs_happy_path(monkeypatch):
    adapter = LeverAdapter(company="acme")

    def fake_fetch(url: str, timeout_s: float = 10.0):
        assert url == "https://api.lever.co/v0/postings/acme?mode=json&limit=25"
        return [{"id": "1", "text": "Engineer", "categories": {"location": "Remote"}}]

    monkeypatch.setattr("jobot.scrapers.ats._fetch_json", fake_fetch)

    postings = await adapter.discover_jobs()
    assert len(postings) == 1
    assert postings[0].title == "Engineer"


@pytest.mark.asyncio
async def test_fetch_json_real_http(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_safe_urlopen(url, **kwargs):
        return FakeResp()

    monkeypatch.setattr("jobot.scrapers.ats.safe_urlopen", fake_safe_urlopen)
    assert await asyncio.to_thread(_fetch_json, "https://example.test/feed") == {"ok": True}


@pytest.mark.asyncio
async def test_fetch_json_decodes_utf8(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return '{"title": "caf\u00e9"}'.encode("utf-8")

    def fake_safe_urlopen(url, **kwargs):
        return FakeResp()

    monkeypatch.setattr("jobot.scrapers.ats.safe_urlopen", fake_safe_urlopen)
    data = await asyncio.to_thread(_fetch_json, "https://example.test/feed")
    assert data == {"title": "caf\u00e9"}