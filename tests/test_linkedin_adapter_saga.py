"""T4.2 — LinkedIn Easy Apply saga wired into the adapter with honest refusal.

Hermetic: saga_factory/profile_loader injected; no real browser needed.
"""

from pathlib import Path
from tempfile import mkdtemp

import pytest
from test_linkedin_easy_apply import FakeBrowserSession

from jobot.adapters.linkedin import LinkedInAdapter
from jobot.models.domain import Application, ApplicationStatus, PersonalInfo, UserProfile
from jobot.stealth.linkedin_easy_apply import EasyApplyResult, EasyApplySaga

JOB_URL = "https://www.linkedin.com/jobs/view/42"


def _profile() -> UserProfile:
    return UserProfile(
        profile_id="p_t42",
        personal_info=PersonalInfo(
            first_name="Aryan", last_name="Sharma", email="aryan@example.com", phone="+911234567890"
        ),
        skills=["Python"],
    )


def _app() -> Application:
    return Application(
        application_id="app_li",
        job_id="42",
        site="linkedin",
        idempotency_key="key_li",
        job_url=JOB_URL,
    )


class FakeSaga:
    def __init__(self, submit_ok: bool = True, verify_ok: bool = True):
        self.submit_ok = submit_ok
        self.verify_ok = verify_ok
        self.run_called = False
        self.verify_called = False

    async def run(self, job_url: str, profile: UserProfile) -> EasyApplyResult:
        self.run_called = True
        return EasyApplyResult(
            success=self.submit_ok,
            status="verify",
            job_url=job_url,
            reason="submitted" if self.submit_ok else "No Easy Apply button",
        )

    async def verify_submitted(self, job_url: str) -> EasyApplyResult:
        self.verify_called = True
        return EasyApplyResult(
            success=self.verify_ok,
            status="verify",
            job_url=job_url,
            evidence_shots=["shot.png"],
            reason="marker visible" if self.verify_ok else "no marker",
        )


@pytest.mark.asyncio
async def test_adapter_fill_form_refused_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = LinkedInAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.fill_form(_app(), _profile(), _app())


@pytest.mark.asyncio
async def test_adapter_submit_refused_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = LinkedInAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.submit_application(_app())


@pytest.mark.asyncio
async def test_adapter_verify_refused_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = LinkedInAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.verify_submission(_app())


@pytest.mark.asyncio
async def test_adapter_fill_form_profile_grounded_with_live_browser(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    adapter = LinkedInAdapter()
    form = await adapter.fill_form(_app(), _profile(), _app())
    assert form["email"] == "aryan@example.com"
    assert form["name"] == "Aryan Sharma"


async def _fake_browser():
    return FakeBrowserSession()


@pytest.mark.asyncio
async def test_adapter_submit_runs_saga_on_success(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    saga = FakeSaga(submit_ok=True)
    adapter = LinkedInAdapter(
        saga_factory=lambda browser: saga,  # type: ignore[arg-type]
        profile_loader=_profile,
        browser_provider=_fake_browser,
    )
    app = _app()
    ok = await adapter.submit_application(app)
    assert ok is True
    assert saga.run_called is True
    assert app.status == ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_adapter_submit_honest_failure_when_saga_fails(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    saga = FakeSaga(submit_ok=False)
    adapter = LinkedInAdapter(
        saga_factory=lambda browser: saga,  # type: ignore[arg-type]
        profile_loader=_profile,
        browser_provider=_fake_browser,
    )
    app = _app()
    ok = await adapter.submit_application(app)
    assert ok is False
    assert app.status != ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_adapter_verify_uses_saga_marker(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    saga = FakeSaga(verify_ok=True)
    adapter = LinkedInAdapter(
        saga_factory=lambda browser: saga,  # type: ignore[arg-type]
        profile_loader=_profile,
        browser_provider=_fake_browser,
    )
    app = _app()
    result = await adapter.verify_submission(app)
    assert result.success is True
    assert saga.verify_called is True
    assert result.confirmation_id == "42"
    assert app.status == ApplicationStatus.VERIFIED


@pytest.mark.asyncio
async def test_adapter_verify_no_marker_is_honest_failure(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    saga = FakeSaga(verify_ok=False)
    adapter = LinkedInAdapter(
        saga_factory=lambda browser: saga,  # type: ignore[arg-type]
        profile_loader=_profile,
        browser_provider=_fake_browser,
    )
    result = await adapter.verify_submission(_app())
    assert result.success is False
    assert result.confirmation_id is None


@pytest.mark.asyncio
async def test_adapter_submit_no_job_url_fails(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    adapter = LinkedInAdapter(profile_loader=_profile)
    app = _app()
    app.job_url = ""
    ok = await adapter.submit_application(app)
    assert ok is False


@pytest.mark.asyncio
async def test_saga_verify_submitted_hermetic():
    browser = FakeBrowserSession()
    saga = EasyApplySaga(browser, evidence_dir=Path(mkdtemp()))
    result = await saga.verify_submitted(JOB_URL)
    assert result.success is False
    assert "No success marker" in result.reason

    browser.page.show("h3:has-text('Submitted')")
    result2 = await saga.verify_submitted(JOB_URL)
    assert result2.success is True
    assert result2.evidence_shots
