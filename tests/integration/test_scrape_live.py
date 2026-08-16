"""Live scraper integration tests — opt-in.

These hit real job boards/ATS APIs, so the default `pytest` run skips them:
    $env:JOBOT_RUN_LIVE_SCRAPE=1; pytest tests/integration/test_scrape_live.py

Exit criteria (plan.md:325): 50+ real postings via `jobot scrape linkedin`,
and dedup reduces the repost rate by ≥80% on synthetic corpus (unit-tested in
tests/test_scrapers_dedup.py).
"""

import os

import pytest

from jobot.scrapers.ats import AshbyAdapter, LeverAdapter, SmartRecruitersAdapter
from jobot.scrapers.jobspy import JobSpyAdapter, JobSpyNotInstalledError

pytestmark = pytest.mark.skipif(
    os.getenv("JOBOT_RUN_LIVE_SCRAPE") != "1",
    reason="live scraper tests opt-in via JOBOT_RUN_LIVE_SCRAPE=1",
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jobspy_linkedin_live():
    """plan.md exit criterion: live LinkedIn scrape returns real postings."""
    try:
        adapter = JobSpyAdapter("linkedin", delay_s=1.0)
    except Exception:  # noqa: BLE001
        pytest.skip("python-jobspy library not installed (--no-deps recipe)")
    postings = await adapter.discover_jobs(
        keywords="senior backend", location="San Francisco", limit=5, hours_old=72
    )
    assert len(postings) >= 1
    assert postings[0].title
    assert postings[0].url.startswith("http")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jobspy_missing_library_clean_error(monkeypatch):
    """Without the library the adapter must fail cleanly (never fabricate)."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jobspy":
            raise ModuleNotFoundError("No module named 'jobspy'", name="jobspy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(JobSpyNotInstalledError):
        await JobSpyAdapter("linkedin", delay_s=0).discover_jobs()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lever_live():
    postings = await LeverAdapter().discover_jobs(company="toptal", limit=3)
    assert len(postings) >= 1
    assert postings[0].title
    assert postings[0].url.startswith("https://jobs.lever.co/")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ashby_live():
    postings = await AshbyAdapter().discover_jobs(company="notion", limit=3)
    assert len(postings) >= 1
    assert postings[0].title


@pytest.mark.integration
@pytest.mark.asyncio
async def test_smartrecruiters_live():
    postings = await SmartRecruitersAdapter().discover_jobs(company="adidas", limit=3)
    assert len(postings) >= 1
    assert postings[0].title


@pytest.mark.integration
@pytest.mark.asyncio
async def test_careers_scanner_live():
    from jobot.scrapers.careers import CareerPageScanner

    postings = await CareerPageScanner().discover_jobs(limit=5)
    assert len(postings) >= 1
    assert postings[0].company in {"webflow", "figma", "vercel", "notion", "benchling"}