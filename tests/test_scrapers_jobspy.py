"""JobSpyAdapter tests — library is faked via sys.modules (never required in CI)."""

import sys
import types

import pytest

from jobot.scrapers.exceptions import JobSpyNotInstalledError
from jobot.scrapers.jobspy import JOBS_BOARDS, JobSpyAdapter, _cell


class FakeSeries:
    """Dict-like stand-in for a pandas Series row (duck-typed _cell)."""

    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]


class FakeFrame:
    def __init__(self, rows):
        self._rows = rows

    def iterrows(self):
        return iter(enumerate(self._rows))


class FakeJobSpy:
    calls: list = []

    def scrape_jobs(self, **kwargs):
        FakeJobSpy.calls.append(kwargs)
        rows = [
            {
                "job_url": "https://linkedin.com/jobs/view/1",
                "title": "Senior Backend Engineer",
                "company_name": "Acme",
                "location": "San Francisco, CA",
                "description": "Python, Go, distributed systems.",
            },
            {"job_url": "", "title": "Frontend Engineer", "company_name": "Beta"},
            {"job_url": "https://linkedin.com/jobs/view/3", "title": "  ", "company_name": "Gamma"},
        ]
        return FakeFrame([FakeSeries(r) for r in rows])


@pytest.fixture
def fake_jobspy(monkeypatch):
    fake = types.ModuleType("jobspy")
    fake.scrape_jobs = FakeJobSpy().scrape_jobs
    monkeypatch.setitem(sys.modules, "jobspy", fake)
    FakeJobSpy.calls = []
    return fake


def test_boards_known():
    assert "linkedin" in JOBS_BOARDS
    assert "indeed" in JOBS_BOARDS
    assert "naukri" in JOBS_BOARDS


def test_unknown_board_rejected():
    with pytest.raises(ValueError):
        JobSpyAdapter("mystery_board")


def test_jobspy_missing_raises_clear_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jobspy":
            raise ModuleNotFoundError("No module named 'jobspy'", name="jobspy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    adapter = JobSpyAdapter("linkedin")

    with pytest.raises(JobSpyNotInstalledError):
        adapter._load_jobspy()


@pytest.mark.asyncio
async def test_discover_jobs_maps_rows(fake_jobspy):
    adapter = JobSpyAdapter("linkedin", delay_s=0)
    postings = await adapter.discover_jobs(
        keywords="senior backend", location="San Francisco", limit=10
    )

    assert len(postings) == 2
    p = postings[0]
    assert p.site == "linkedin"
    assert p.job_id == "https://linkedin.com/jobs/view/1"
    assert p.title == "Senior Backend Engineer"
    assert p.company == "Acme"
    assert p.location == "San Francisco, CA"
    assert p.description == "Python, Go, distributed systems."

    # missing URL -> deterministic digest URL; blank title rows skipped
    assert postings[1].url.startswith("https://linkedin.jobs/job/")


@pytest.mark.asyncio
async def test_discover_jobs_passes_params(fake_jobspy):
    adapter = JobSpyAdapter("indeed", delay_s=0)
    await adapter.discover_jobs(
        keywords="devops", location="London", limit=5, hours_old=24, country_indeed="GBR"
    )

    call = FakeJobSpy.calls[-1]
    assert call["site_name"] == "indeed"
    assert call["search_term"] == "devops"
    assert call["location"] == "London"
    assert call["results_wanted"] == 5
    assert call["hours_old"] == 24
    assert call["country_indeed"] == "GBR"
    assert call["verbose"] is False


@pytest.mark.asyncio
async def test_discover_jobs_optional_flags(fake_jobspy):
    adapter = JobSpyAdapter("google", delay_s=0, proxies=["http://p1:8080"])
    await adapter.discover_jobs(keywords="sre", is_remote=True, job_type="fulltime")

    call = FakeJobSpy.calls[-1]
    assert call["is_remote"] is True
    assert call["job_type"] == "fulltime"
    assert call["proxies"] == ["http://p1:8080"]


@pytest.mark.asyncio
async def test_circuit_breaker_returns_empty_on_failure(fake_jobspy, monkeypatch):
    adapter = JobSpyAdapter("linkedin", delay_s=0)

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(adapter, "_scrape", boom)

    async def fake_breaker(*args, **kwargs):
        return None

    monkeypatch.setattr(adapter.breaker, "execute_with_retry", fake_breaker)

    assert await adapter.discover_jobs() == []


def test_cell_nan_returns_default():
    assert _cell(FakeSeries({"x": float("nan")}), "x", "dflt") == "dflt"
    assert _cell(FakeSeries({"x": None}), "x", "dflt") == "dflt"
    assert _cell(FakeSeries({"x": 5}), "x", "dflt") == 5
    assert _cell(FakeSeries({}), "missing", "dflt") == "dflt"
