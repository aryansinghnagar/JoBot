"""Phase 3 T3.5/T3.7: greenhouse honest verify + resume attachment; linkedin honesty; CLI."""

import base64
import json
import urllib.request

import pytest
from jobot.adapters.greenhouse import GreenhouseAdapter
from jobot.adapters.linkedin import LinkedInAdapter
from jobot.models.domain import Application, JobPosting, PersonalInfo, UserProfile


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


def _greenhouse_app(resume_path=None):
    form = {"first_name": "Aryan", "last_name": "Sharma", "email": "a@b.com", "phone": "+91"}
    if resume_path:
        form["resume_path"] = str(resume_path)
    return Application(
        application_id="app_gh",
        job_id="999",
        site="greenhouse",
        idempotency_key="k",
        job_url="https://boards.greenhouse.io/acme/jobs/999",
        form_values=form,
    )


@pytest.mark.asyncio
async def test_greenhouse_verify_honest_without_confirmation():
    adapter = GreenhouseAdapter()
    result = await adapter.verify_submission(_greenhouse_app())
    assert result.success is False
    assert "no confirmation" in result.reason.lower()


@pytest.mark.asyncio
async def test_greenhouse_verify_with_confirmation():
    adapter = GreenhouseAdapter()
    app = _greenhouse_app()
    app.form_values["_greenhouse_confirmation_id"] = "gh_app_1"
    result = await adapter.verify_submission(app)
    assert result.success is True
    assert result.confirmation_id == "gh_app_1"


@pytest.mark.asyncio
async def test_greenhouse_submit_attaches_resume(monkeypatch, tmp_path):
    adapter = GreenhouseAdapter()
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4 fake")

    captured = {}

    def fake_post(url, *, data=None, headers=None, timeout=10.0, method=None, allow_private_hosts=False):
        captured["body"] = json.loads(data.decode("utf-8"))
        return FakeResponse({"id": "gh_app_1"}, status=201)

    monkeypatch.setattr("jobot.adapters.greenhouse.safe_urlopen", fake_post)
    app = _greenhouse_app(resume_path=resume)
    ok = await adapter.submit_application(app)

    assert ok is True
    payload = captured["body"]
    assert payload["resume"]["filename"] == "resume.pdf"
    assert payload["resume"]["content_base64"] == base64.b64encode(b"%PDF-1.4 fake").decode("ascii")
    assert app.form_values["_greenhouse_confirmation_id"] == "gh_app_1"


@pytest.mark.asyncio
async def test_linkedin_adapter_is_honest():
    adapter = LinkedInAdapter()
    job = JobPosting(job_id="x", site="linkedin", url="https://linkedin.com/jobs/view/1", title="t", company="c")
    profile = UserProfile(profile_id="p", personal_info=PersonalInfo(first_name="A", email="a@b.com"))

    with pytest.raises(NotImplementedError):
        await adapter.parse_job_posting("https://linkedin.com/jobs/view/1")
    with pytest.raises(NotImplementedError):
        await adapter.fill_form(job, profile, _greenhouse_app())
    with pytest.raises(NotImplementedError):
        await adapter.submit_application(_greenhouse_app())


def test_cli_apply_missing_profile(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from jobot.cli.main import app

    runner = CliRunner()
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    result = runner.invoke(app, ["apply", "--url", "https://boards.greenhouse.io/acme/jobs/1"])
    assert result.exit_code == 1
    assert "profile missing" in result.stdout.lower()


def test_cli_resume_templates(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from jobot.cli.main import app

    runner = CliRunner()
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    result = runner.invoke(app, ["resume", "templates"])
    assert result.exit_code == 0
    assert "default" in result.stdout
    assert "modern" in result.stdout
    assert "classic" in result.stdout


def test_cli_resume_ats_check(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from jobot.cli.main import app
    from jobot.documents import ResumeExporter
    from jobot.models.domain import (
        CompensationDetails,
        Education,
        PersonalInfo,
        UserProfile,
        WorkExperience,
    )

    profile = UserProfile(
        profile_id="p",
        personal_info=PersonalInfo(
            first_name="Aryan", last_name="Sharma", email="a@example.com", phone="+91"
        ),
        compensation=CompensationDetails(notice_period_days=30),
        skills=["Python", "FastAPI"],
        experiences=[
            WorkExperience(
                title="Engineer",
                company="Acme",
                start_date="2021",
                end_date="Present",
                description="Built REST APIs in Python with FastAPI and PostgreSQL; owned CI/CD; mentored juniors.",
            ),
            WorkExperience(
                title="Developer",
                company="Beta",
                start_date="2019",
                end_date="2021",
                description="Developed Django features; integrated payments; wrote unit tests.",
            ),
            WorkExperience(
                title="Junior Dev",
                company="Gamma",
                start_date="2017",
                end_date="2019",
                description="Maintained tooling and reporting dashboards.",
            ),
        ],
        education=[Education(degree="B.Tech", field_of_study="CS", institution="IIT", start_year=2017)],
    )
    resumes_dir = tmp_path / ".jobot" / "resumes"
    ResumeExporter().export_resume_pdf(profile, engine="fallback", output_dir=resumes_dir)

    runner = CliRunner()
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    result = runner.invoke(app, ["resume", "ats-check"])
    assert result.exit_code == 0
    assert "PASS" in result.stdout