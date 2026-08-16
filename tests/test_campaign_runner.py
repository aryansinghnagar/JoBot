"""Phase 5 T4.1: campaign runner wired to ApplyOrchestrator + LLM cost gate."""

from pathlib import Path

import pytest
from jobot.asp.orchestrator import ApplyResult
from jobot.discovery.engine import JobMatchResult
from jobot.models.domain import (
    ApplicationStatus,
    JobPosting,
    PersonalInfo,
    TrustLevel,
    UserProfile,
)
from jobot.runner import ContinuousCampaignRunner


def make_profile() -> UserProfile:
    return UserProfile(
        profile_id="p_campaign",
        personal_info=PersonalInfo(first_name="Aryan", last_name="Sharma", email="a@example.com"),
    )


def make_match(job_id: str = "job1", site: str = "mock_ats") -> JobMatchResult:
    return JobMatchResult(
        posting=JobPosting(
            job_id=job_id,
            site=site,
            url=f"http://ats/{job_id}",
            title="Backend Engineer",
            company="Mock Corp",
            location="B",
            description="Python role.",
            parsed_skills=["Python"],
        ),
        match_score=0.9,
        matching_skills=["Python"],
        missing_skills=[],
        recommendation="HIGH_FIT",
    )


class FakeVault:
    def load_encrypted_profile(self, path):
        return make_profile()


class FakeDiscovery:
    def __init__(self, matches):
        self.matches = matches
        self.portals = []

    async def discover_matching_jobs(self, *args, **kwargs):
        return self.matches


class FakeOrchestrator:
    def __init__(self, status="verified"):
        self.status = status
        self.applied = []

    async def apply(self, job, profile, auto_approve=False, dry_run=False, **kwargs):
        self.applied.append(job.job_id)
        return ApplyResult(
            saga_id=f"saga-{job.job_id}",
            job_id=job.job_id,
            app_status=self.status,
            dry_run=False,
        )


class FakeRouter:
    def __init__(self, spent=0.0, budget=5.0):
        self.current_spent_usd = spent
        self.daily_budget_usd = budget


@pytest.mark.asyncio
async def test_campaign_routes_through_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".jobot" / "profiles").mkdir(parents=True)
    (tmp_path / ".jobot" / "profiles" / "default.enc").write_text("x", encoding="utf-8")

    orch = FakeOrchestrator()
    runner = ContinuousCampaignRunner(
        root_dir=tmp_path,
        orchestrator=orch,
        router=FakeRouter(),
        discovery_factory=lambda portal: FakeDiscovery([make_match()]),
    )
    runner.vault = FakeVault()

    total = await runner.run_continuous_campaign(goal_count=1, max_iterations=5)
    assert total == 1
    assert orch.applied == ["job1"]
    log = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert "Mock Corp" in log
    assert "VERIFIED" in log


@pytest.mark.asyncio
async def test_campaign_rejected_does_not_increment(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".jobot" / "profiles").mkdir(parents=True)
    (tmp_path / ".jobot" / "profiles" / "default.enc").write_text("x", encoding="utf-8")

    runner = ContinuousCampaignRunner(
        root_dir=tmp_path,
        orchestrator=FakeOrchestrator(status="rejected"),
        router=FakeRouter(),
        discovery_factory=lambda portal: FakeDiscovery([make_match()]),
    )
    runner.vault = FakeVault()

    total = await runner.run_continuous_campaign(goal_count=5, max_iterations=3)
    assert total == 0


@pytest.mark.asyncio
async def test_campaign_cost_gate_halts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".jobot" / "profiles").mkdir(parents=True)
    (tmp_path / ".jobot" / "profiles" / "default.enc").write_text("x", encoding="utf-8")

    orch = FakeOrchestrator()
    runner = ContinuousCampaignRunner(
        root_dir=tmp_path,
        orchestrator=orch,
        router=FakeRouter(spent=6.0, budget=5.0),
        discovery_factory=lambda portal: FakeDiscovery([make_match()]),
    )
    runner.vault = FakeVault()

    total = await runner.run_continuous_campaign(goal_count=5, max_iterations=3)
    assert total == 0
    assert orch.applied == []
    assert "COST" in capsys.readouterr().out.upper()


@pytest.mark.asyncio
async def test_campaign_missing_profile_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    runner = ContinuousCampaignRunner(root_dir=tmp_path, orchestrator=FakeOrchestrator())
    assert await runner.run_continuous_campaign() == 0


@pytest.mark.asyncio
async def test_campaign_blocked_by_policy_skips(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".jobot" / "profiles").mkdir(parents=True)
    (tmp_path / ".jobot" / "profiles" / "default.enc").write_text("x", encoding="utf-8")

    class BlockingPolicy:
        def check_application_policy(self, job, profile, stub, daily_submitted_count=0):
            from jobot.policy.engine import PolicyEvaluationResult

            return PolicyEvaluationResult(
                allowed=False,
                requires_approval=False,
                violations=[],
                blocking_reason="Daily limit reached",
            )

    orch = FakeOrchestrator()
    runner = ContinuousCampaignRunner(
        root_dir=tmp_path,
        orchestrator=orch,
        router=FakeRouter(),
        discovery_factory=lambda portal: FakeDiscovery([make_match()]),
    )
    runner.vault = FakeVault()
    runner.policy_engine = BlockingPolicy()

    total = await runner.run_continuous_campaign(goal_count=5, max_iterations=2)
    assert total == 0
    assert orch.applied == []