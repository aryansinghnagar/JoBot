"""Phase 4 WS4: CareerAnalytics — skill-gap + salary benchmarking."""

import json
import os

import pytest
from jobot.analytics.salary import SalaryBenchmarker
from jobot.analytics.skill_gap import SkillGapAnalyzer
from jobot.llm.router import DEGRADATION_TEXT
from jobot.models.domain import (
    CompensationDetails,
    Education,
    JobPosting,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)
from jobot.storage.db import DatabaseManager
from typer.testing import CliRunner

from jobot.cli.main import app


def make_profile() -> UserProfile:
    return UserProfile(
        profile_id="p_ca",
        personal_info=PersonalInfo(
            first_name="Aryan",
            last_name="Sharma",
            email="aryan@example.com",
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI"],
        experiences=[
            WorkExperience(
                title="Engineer",
                company="Mock Corp",
                start_date="2021",
                end_date="Present",
                description="Built REST APIs in Python.",
            )
        ],
        education=[Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)],
    )


class FakeRouter:
    def __init__(self, reply=None, degrade=False):
        self.reply = reply
        self.degrade = degrade

    async def generate_text(self, prompt, **kwargs):
        if self.degrade:
            return DEGRADATION_TEXT
        return self.reply or '["Learn Kubernetes", "Learn Terraform", "Learn Spark"]'


@pytest.fixture
def seeded_db(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "ca.db")
    db.save_job_posting(
        JobPosting(
            job_id="J1",
            site="mock_ats",
            url="http://x/1",
            title="Backend Engineer",
            company="C1",
            location="B",
            description="Python FastAPI Kubernetes role.",
            parsed_skills=["Python", "FastAPI", "Kubernetes"],
        )
    )
    db.save_job_posting(
        JobPosting(
            job_id="J2",
            site="mock_ats",
            url="http://x/2",
            title="ML Engineer",
            company="C2",
            location="B",
            description="ML role.",
            parsed_skills=["Python", "PyTorch", "Kubernetes"],
        )
    )
    return db


def test_skill_gap_analysis(seeded_db):
    analyzer = SkillGapAnalyzer(db=seeded_db, router=FakeRouter())
    report = analyzer.analyze(make_profile())
    assert report.total_postings == 2
    assert report.top_demanded[0].skill == "python"
    assert "python" not in [g.skill for g in report.gaps]
    gap_skills = [g.skill for g in report.gaps]
    assert "kubernetes" in gap_skills
    assert "pytorch" in gap_skills
    assert report.gaps[0].skill == "kubernetes"  # demand-ordered


def test_skill_gap_recommendations_degrade_gracefully(seeded_db):
    analyzer = SkillGapAnalyzer(db=seeded_db, router=FakeRouter(degrade=True))
    report = analyzer.analyze(make_profile())
    assert any("kubernetes" in r for r in report.recommendations)
    assert "saved postings" in report.sourced_from


def test_skill_gap_empty_db(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "empty.db")
    analyzer = SkillGapAnalyzer(db=db, router=FakeRouter())
    report = analyzer.analyze(make_profile())
    assert report.total_postings == 0
    assert report.gaps == []
    assert "No skill gaps" in report.recommendations[0]


def test_salary_yaml_lookup():
    bm = SalaryBenchmarker()
    band = bm.benchmark("backend", "India", "INR")
    assert band is not None
    assert band.currency == "INR"
    assert band.p50 >= band.p25
    assert band.p75 >= band.p50
    assert "local benchmark data" in band.source


def test_salary_unknown_role_returns_none():
    bm = SalaryBenchmarker()
    assert bm.benchmark("astronaut", "India", "INR") is None


def test_salary_live_fetch_falls_back_to_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_SALARY", "1")
    bm = SalaryBenchmarker(
        cache_path=tmp_path / "cache.json",
        http_getter=lambda url: (200, "<html>only one $120,000 figure</html>"),
    )
    band = bm.benchmark("backend", "India", "INR")
    assert band is not None
    assert "local benchmark data" in band.source


def test_salary_live_fetch_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_SALARY", "1")
    calls = []

    def getter(url):
        calls.append(url)
        return (200, "$100,000 $120,000 $140,000 $160,000 $180,000 $200,000 $220,000 $240,000")

    bm = SalaryBenchmarker(cache_path=tmp_path / "cache.json", http_getter=getter)
    band1 = bm.benchmark("backend", "India", "INR")
    band2 = bm.benchmark("backend", "India", "INR")
    assert len(calls) == 1
    assert band1.source == band2.source == "live levels.fyi fetch (best-effort)"
    assert band1.p50 >= band1.p25


def test_cli_salary(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["salary", "--role", "backend", "--region", "India"])
    assert result.exit_code == 0
    assert "backend" in result.stdout
    assert "local benchmark data" in result.stdout.lower()


def test_cli_skill_gap_missing_profile(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["skill-gap"])
    assert result.exit_code == 1
    assert "profile" in result.stdout.lower()