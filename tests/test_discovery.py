"""JobDiscoveryEngine tests — hermetic (fake scrapers, no live network)."""

import pytest

from jobot.discovery.engine import JobDiscoveryEngine, UNSCRAPABLE_BOARDS
from jobot.models.domain import JobPosting, PersonalInfo, UserProfile


class FakeScraper:
    def __init__(self, postings: list):
        self._postings = postings
        self.calls = []

    async def discover_jobs(self, **kwargs):
        self.calls.append(kwargs)
        return self._postings


def make_posting(title: str, site: str = "linkedin") -> JobPosting:
    return JobPosting(
        job_id=f"{site}:{title}",
        site=site,
        url=f"https://{site}.com/jobs/{title}",
        title=title,
        company="Acme Corp",
        location="Remote",
        parsed_skills=["Python", "FastAPI"],
    )


@pytest.mark.asyncio
async def test_job_discovery_and_matching(monkeypatch, tmp_path):
    import jobot.discovery.engine as eng
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(tmp_path / "discovery.db")
    discovery = JobDiscoveryEngine(
        active_portals=["naukri", "linkedin"], db=db, dedup=eng.DedupService(db=db)
    )
    fake = FakeScraper([make_posting("Python Engineer")])
    monkeypatch.setattr(discovery, "_scraper_for", lambda portal, companies: fake)

    profile = UserProfile(
        profile_id="p_disc",
        personal_info=PersonalInfo(first_name="Rahul", last_name="Sharma"),
        skills=["Python", "FastAPI", "SQLite"],
    )

    posting = make_posting("Python Engineer")
    match_res = discovery.evaluate_match(posting, profile)
    assert match_res.match_score == 1.0
    assert match_res.recommendation == "HIGH_FIT"
    assert "Python" in match_res.matching_skills

    discovered = await discovery.discover_matching_jobs(profile, target_title="Python Developer")
    assert len(discovered) == 1
    assert all(d.match_score >= 0.20 for d in discovered)
    assert fake.calls == [{"keywords": "Python Developer", "location": "", "limit": 2}]


@pytest.mark.asyncio
async def test_discovery_no_scraper_portals_skipped(monkeypatch):
    discovery = JobDiscoveryEngine(active_portals=["naukri", "linkedin"])
    monkeypatch.setattr(discovery, "_scraper_for", lambda portal, companies: None)

    profile = UserProfile(
        profile_id="p_skip",
        personal_info=PersonalInfo(first_name="Rahul"),
        skills=["Python"],
    )

    assert await discovery.discover_matching_jobs(profile) == []


@pytest.mark.asyncio
async def test_discovery_scraper_error_skips_portal(monkeypatch):
    discovery = JobDiscoveryEngine(active_portals=["linkedin"])

    class BrokenScraper:
        async def discover_jobs(self, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(discovery, "_scraper_for", lambda portal, companies: BrokenScraper())

    profile = UserProfile(
        profile_id="p_err",
        personal_info=PersonalInfo(first_name="Rahul"),
        skills=["Python"],
    )

    assert await discovery.discover_matching_jobs(profile) == []


def test_unscrapable_boards_filtered_from_active():
    discovery = JobDiscoveryEngine(active_portals=["workday", "linkedin", "naukri"])
    assert discovery.active_portals == ["linkedin"]
    assert "workday" in UNSCRAPABLE_BOARDS
    assert "naukri" in UNSCRAPABLE_BOARDS


def test_discovery_requires_companies_for_family_portals(monkeypatch):
    discovery = JobDiscoveryEngine(active_portals=["lever"])
    assert discovery._scraper_for("lever", []) is None


@pytest.mark.asyncio
async def test_discovery_dedup_applies(monkeypatch, tmp_path):
    import jobot.discovery.engine as eng
    from jobot.storage.db import DatabaseManager

    db = DatabaseManager(tmp_path / "engine.db")
    discovery = JobDiscoveryEngine(
        active_portals=["linkedin"], db=db, dedup=eng.DedupService(db=db)
    )
    dup_posts = [
        make_posting("Senior Backend Engineer", "linkedin"),
        make_posting("Senior Backend Engineer", "linkedin"),
    ]
    fake = FakeScraper(dup_posts)
    monkeypatch.setattr(discovery, "_scraper_for", lambda portal, companies: fake)

    profile = UserProfile(
        profile_id="p_dedup",
        personal_info=PersonalInfo(first_name="Rahul"),
        skills=["Python", "FastAPI"],
    )

    discovered = await discovery.discover_matching_jobs(profile)
    assert len(discovered) == 1
