"""P1.1/P1.2 — honest Naukri submit/verify (no fabrication without a real browser)."""

from typing import Any, List, Optional

import pytest

from jobot.adapters.naukri.adapter import NaukriAdapter
from jobot.adapters.naukri.submit import NaukriSubmitter
from jobot.adapters.naukri.verify import NaukriVerifier
from jobot.models.domain import Application, ApplicationStatus


def _app(
    job_id: str = "job-101", job_url: str = "https://www.naukri.com/job/job-101"
) -> Application:
    return Application(
        application_id="app_nk",
        job_id=job_id,
        site="naukri",
        idempotency_key="key_nk",
        job_url=job_url,
    )


class FakeLocator:
    def __init__(
        self,
        count: int = 0,
        texts: list[str] | None = None,
        fail_click: bool = False,
    ) -> None:
        self._count = count
        self._texts = texts or []
        self.fail_click = fail_click
        self.first = self

    async def count(self) -> int:
        return self._count

    async def all_text_contents(self) -> list[str]:
        return list(self._texts)

    async def click(self, timeout: int | None = None) -> None:
        if self.fail_click:
            raise RuntimeError("click failed")


class FakePage:
    def __init__(
        self,
        body_text: str = "",
        apply_button: bool = False,
        confirmed: bool = False,
        login_wall: bool = False,
        rows: list[str] | None = None,
    ) -> None:
        self.body_text = body_text
        self.apply_button = apply_button
        self.confirmed = confirmed
        self.login_wall = login_wall
        self.rows = rows
        self.gotos: list[str] = []
        self.clicked_apply = False

    async def goto(self, url: str, wait_until: str | None = None) -> None:
        self.gotos.append(url)

    def locator(self, selector: str) -> FakeLocator:
        if "body" in selector:
            return FakeLocator(count=1, texts=[self.body_text])
        if self.rows is not None and "job" in selector:
            return FakeLocator(count=1, texts=list(self.rows))
        if self.login_wall and ("usernameField" in selector or "login-form" in selector):
            return FakeLocator(count=1)
        if "Apply" in selector:
            return FakeLocator(
                count=1 if self.apply_button else 0,
                fail_click=not self.apply_button,
            )
        if "Applied" in selector:
            return FakeLocator(count=1 if "already applied" in self.body_text else 0)
        if "text=" in selector and self.confirmed:
            return FakeLocator(count=1)
        if selector in ("body",):
            return FakeLocator(count=1, texts=[self.body_text])
        return FakeLocator(count=0)


@pytest.mark.asyncio
async def test_submit_refuses_without_page():
    submitter = NaukriSubmitter()
    app = _app()
    ok = await submitter.submit(app, page=None)
    assert ok is False
    assert app.status != ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_submit_refuses_on_login_wall():
    page = FakePage(login_wall=True)
    submitter = NaukriSubmitter()
    ok = await submitter.submit(_app(), page=page)
    assert ok is False


@pytest.mark.asyncio
async def test_submit_confirms_real_submission():
    page = FakePage(
        apply_button=True,
        confirmed=True,
        body_text="Apply Now",
    )
    submitter = NaukriSubmitter()
    app = _app()
    ok = await submitter.submit(app, page=page)
    assert ok is True
    assert app.status == ApplicationStatus.SUBMITTED
    assert page.gotos[0] == app.job_url


@pytest.mark.asyncio
async def test_submit_no_confirmation_is_honest_failure():
    page = FakePage(apply_button=True, confirmed=False, body_text="Apply Now")
    submitter = NaukriSubmitter()
    app = _app()
    ok = await submitter.submit(app, page=page)
    assert ok is False
    assert app.status != ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_submit_no_apply_button_fails():
    page = FakePage(apply_button=False, confirmed=False, body_text="No button here")
    submitter = NaukriSubmitter()
    ok = await submitter.submit(_app(), page=page)
    assert ok is False


@pytest.mark.asyncio
async def test_submit_detects_already_applied():
    page = FakePage(apply_button=False, body_text="You already applied on 12 Aug 2026")
    submitter = NaukriSubmitter()
    app = _app()
    ok = await submitter.submit(app, page=page)
    assert ok is True
    assert app.status == ApplicationStatus.SUBMITTED


@pytest.mark.asyncio
async def test_verify_refuses_without_page():
    result = await NaukriVerifier().verify(_app(), page=None)
    assert result.success is False
    assert "No browser page" in result.reason


@pytest.mark.asyncio
async def test_verify_requires_authentication():
    page = FakePage(login_wall=True)
    result = await NaukriVerifier().verify(_app(), page=page)
    assert result.success is False
    assert "authenticated" in result.reason


@pytest.mark.asyncio
async def test_verify_finds_job_in_dashboard():
    page = FakePage(rows=["Senior Backend Engineer — job-101 — Applied on 15 Aug"])
    result = await NaukriVerifier().verify(_app(), page=page)
    assert result.success is True
    assert result.confirmation_id == "job-101"
    assert page.gotos[0] == "https://www.naukri.com/mnjuser/myapplications"


@pytest.mark.asyncio
async def test_verify_not_found_is_honest_failure():
    page = FakePage(rows=["Frontend Engineer — job-999 — Applied on 1 Aug"])
    result = await NaukriVerifier().verify(_app(), page=page)
    assert result.success is False
    assert "not found" in result.reason
    assert result.confirmation_id is None


@pytest.mark.asyncio
async def test_verify_unparseable_dashboard_fails():
    page = FakePage(rows=None)
    result = await NaukriVerifier().verify(_app(), page=page)
    assert result.success is False
    assert "Could not parse" in result.reason


@pytest.mark.asyncio
async def test_adapter_refuses_submit_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = NaukriAdapter()
    monkeypatch.setattr(adapter, "_jitter_delay", _noop)
    ok = await adapter.submit_application(_app())
    assert ok is False


@pytest.mark.asyncio
async def test_adapter_refuses_verify_without_live_browser(monkeypatch):
    monkeypatch.delenv("JOBOT_RUN_LIVE_BROWSER", raising=False)
    adapter = NaukriAdapter()
    monkeypatch.setattr(adapter, "_jitter_delay", _noop)
    result = await adapter.verify_submission(_app())
    assert result.success is False


@pytest.mark.asyncio
async def test_adapter_wires_browser_page_when_enabled(monkeypatch):
    monkeypatch.setenv("JOBOT_RUN_LIVE_BROWSER", "1")
    adapter = NaukriAdapter()
    monkeypatch.setattr(adapter, "_jitter_delay", _noop)

    async def fake_browser_page() -> FakePage:
        return FakePage(rows=["job-101 — Applied"])

    monkeypatch.setattr(adapter, "_browser_page", fake_browser_page)
    result = await adapter.verify_submission(_app())
    assert result.success is True


async def _noop(*args: Any, **kwargs: Any) -> None:
    return None
