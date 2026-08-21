"""Phase 4 WS2: LoopExecutor — 4-mode scheduler loop (scan/apply/digest/full)."""

import pytest

from jobot.asp.orchestrator import ApplyResult
from jobot.discovery.engine import JobMatchResult
from jobot.models.domain import (
    CompensationDetails,
    Education,
    JobPosting,
    PersonalInfo,
    UserProfile,
    WorkExperience,
)
from jobot.policy.engine import PolicyEvaluationResult
from jobot.scheduler.loop import MODES, LoopExecutor
from jobot.storage.db import DatabaseManager


def make_profile() -> UserProfile:
    return UserProfile(
        profile_id="p_loop",
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
        education=[
            Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)
        ],
    )


def make_posting(job_id: str = "job1", site: str = "mock_ats") -> JobPosting:
    return JobPosting(
        job_id=job_id,
        site=site,
        url=f"http://ats/{job_id}",
        title="Senior Backend Engineer",
        company="Mock Corp",
        location="Bangalore",
        description="Python backend role.",
        parsed_skills=["Python", "FastAPI"],
    )


def make_match(job: JobPosting) -> JobMatchResult:
    return JobMatchResult(
        posting=job,
        match_score=0.9,
        matching_skills=["Python"],
        missing_skills=[],
        recommendation="HIGH_FIT",
    )


class FakeDiscovery:
    def __init__(self, matches):
        self.matches = matches
        self.calls = 0

    async def discover_matching_jobs(self, *args, **kwargs):
        self.calls += 1
        return self.matches


class FakeOrchestrator:
    def __init__(self, statuses=None):
        self.statuses = statuses or {}
        self.applied_jobs = []

    async def apply(self, job, profile, auto_approve=False, dry_run=False, **kwargs):
        self.applied_jobs.append(job.job_id)
        status = self.statuses.get(job.job_id, "submitted")
        return ApplyResult(
            saga_id=f"saga-{job.job_id}",
            job_id=job.job_id,
            app_status=status,
            dry_run=False,
        )


class FakeEmail:
    def __init__(self, ok=True):
        self.ok = ok
        self.sent = []

    def send(self, subject, body_html, body_text=None):
        self.sent.append(subject)
        return self.ok, "sent" if self.ok else "SMTP not configured"


@pytest.fixture
def env(tmp_path):
    db = DatabaseManager(db_path=tmp_path / "loop.db")
    return db


@pytest.mark.asyncio
async def test_scan_only_mode(env):
    job = make_posting()
    loop = LoopExecutor(
        db=env,
        orchestrator=FakeOrchestrator(),
        discovery=FakeDiscovery([make_match(job)]),
        email=FakeEmail(),
    )
    res = await loop.run("scan-only", make_profile(), max_apply=1)
    assert res.mode == "scan-only"
    assert res.discovered == 1
    assert res.applied == 0
    assert env.get_job_posting(job.job_id) is not None


@pytest.mark.asyncio
async def test_apply_only_mode(env):
    job = make_posting()
    orch = FakeOrchestrator({job.job_id: "verified"})
    loop = LoopExecutor(
        db=env,
        orchestrator=orch,
        discovery=FakeDiscovery([make_match(job)]),
        email=FakeEmail(),
    )
    res = await loop.run("apply-only", make_profile(), max_apply=5)
    assert orch.applied_jobs == [job.job_id]
    assert res.applied == 1
    assert res.verified == 1


@pytest.mark.asyncio
async def test_apply_only_honors_max_apply(env):
    jobs = [make_posting(f"job{i}", f"site{i}") for i in range(1, 4)]
    orch = FakeOrchestrator()
    loop = LoopExecutor(
        db=env,
        orchestrator=orch,
        discovery=FakeDiscovery([make_match(j) for j in jobs]),
        email=FakeEmail(),
    )
    res = await loop.run("apply-only", make_profile(), max_apply=2)
    assert len(orch.applied_jobs) == 2
    assert res.applied == 2


@pytest.mark.asyncio
async def test_daily_cap_stops_apply_loop(env):
    job = make_posting(site="mock_ats")
    orch = FakeOrchestrator()
    loop = LoopExecutor(
        db=env,
        orchestrator=orch,
        discovery=FakeDiscovery([make_match(job), make_match(make_posting("job2"))]),
        email=FakeEmail(),
    )

    class CappedPolicy:
        def check_application_policy(self, job, profile, stub, daily):
            return PolicyEvaluationResult(
                allowed=False,
                requires_approval=False,
                violations=[],
                blocking_reason=f"Daily limit of 0 applications reached for site '{job.site}'.",
            )

    loop.policy = CappedPolicy()
    res = await loop.run("apply-only", make_profile(), max_apply=5)
    assert orch.applied_jobs == []
    assert res.blocked == 1
    assert any("daily cap" in n for n in res.notes)


@pytest.mark.asyncio
async def test_digest_only_mode(env):
    email = FakeEmail(ok=True)
    loop = LoopExecutor(
        db=env,
        orchestrator=FakeOrchestrator(),
        discovery=FakeDiscovery([]),
        email=email,
    )
    res = await loop.run("digest-only", make_profile())
    assert res.digest_sent is True
    assert email.sent and "weekly digest" in email.sent[0]


@pytest.mark.asyncio
async def test_full_loop_mode(env):
    job = make_posting()
    email = FakeEmail(ok=True)
    orch = FakeOrchestrator({job.job_id: "verified"})
    loop = LoopExecutor(
        db=env,
        orchestrator=orch,
        discovery=FakeDiscovery([make_match(job)]),
        email=email,
    )
    res = await loop.run("full-loop", make_profile(), max_apply=5)
    assert res.discovered == 1
    assert res.applied == 1
    assert res.verified == 1
    assert res.digest_sent is True


@pytest.mark.asyncio
async def test_unknown_mode_raises(env):
    loop = LoopExecutor(db=env, orchestrator=FakeOrchestrator(), email=FakeEmail())
    with pytest.raises(ValueError, match="unknown loop mode"):
        await loop.run("bogus", make_profile())


def test_modes_are_four():
    assert MODES == ("scan-only", "apply-only", "digest-only", "full-loop")


def test_cli_loop_rejects_unknown_mode():
    from typer.testing import CliRunner

    from jobot.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["loop", "--mode", "bogus"])
    assert result.exit_code == 1
    assert "Unknown loop mode" in result.stdout
