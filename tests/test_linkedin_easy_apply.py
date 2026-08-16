"""Hermetic tests for the Easy Apply saga with a fake browser (Phase 3, T3.6).

The saga is exercised against a FakeBrowserSession that simulates the
LinkedIn Easy Apply modal DOM without any real browser. Covers the happy
path, missing Easy Apply button, and unknown modal state.
"""

from pathlib import Path

import pytest
from jobot.stealth.linkedin_easy_apply import EasyApplySaga
from jobot.models.domain import PersonalInfo, UserProfile


class FakeLocator:
    def __init__(self, selector: str, page: "FakePage", index: int = 0):
        self.selector = selector
        self.page = page
        self.index = index
        self.filled: str = ""

    @property
    def first(self) -> "FakeLocator":
        return self

    def nth(self, index: int) -> "FakeLocator":
        return FakeLocator(self.selector, self.page, index=index)

    async def count(self) -> int:
        return self.page.field_count(self.selector)

    async def wait_for(self, state: str, timeout: int = 0) -> None:
        if not self.page.is_selector_visible(self.selector):
            raise TimeoutError(f"selector {self.selector} not visible")

    async def click(self) -> None:
        self.page.on_click(self.selector)

    async def fill(self, value: str) -> None:
        self.filled = value
        self.page.fills.append((self.selector, self.index, value))

    async def get_attribute(self, name: str):
        if "input" in self.selector:
            return {"placeholder": "email", "name": "email", "aria-label": None}.get(name)
        if "textarea" in self.selector:
            return {"placeholder": "Cover note", "name": None, "aria-label": None}.get(name)
        return None

    async def inner_text(self) -> str:
        return "visible text"

    async def press_sequentially(self, value: str, delay: int = 0) -> None:
        await self.fill(value)


class FakePage:
    """Simulates a patchright Page with selector-driven visibility transitions."""

    def __init__(self) -> None:
        self.visible: dict = {
            "button.jobs-apply-button": True,
            "form": False,
            "input": False,
            "textarea": False,
            "button[aria-label*='Next' i]": False,
            "button[aria-label*='Review' i]": False,
            "button[aria-label*='Submit application' i]": False,
            "h3:has-text('Submitted')": False,
        }
        self.fills: list = []
        self.shots: list = []

    def show(self, selector: str) -> None:
        self.visible[selector] = True

    def is_selector_visible(self, selector: str) -> bool:
        return self.visible.get(selector, False)

    def field_count(self, selector: str) -> int:
        if "input" in selector:
            return 1 if self.visible.get("input", False) else 0
        if "textarea" in selector:
            return 1 if self.visible.get("textarea", False) else 0
        if "select" in selector:
            return 0
        return 1 if self.visible.get(selector, False) else 0

    def on_click(self, selector: str) -> None:
        if selector == "button.jobs-apply-button":
            self.show("form")
            self.show("input")
            self.show("textarea")
            self.show("button[aria-label*='Next' i]")
        elif selector == "button[aria-label*='Next' i]":
            self.visible["button[aria-label*='Next' i]"] = False
            self.visible["input"] = False
            self.visible["textarea"] = False
            self.show("button[aria-label*='Review' i]")
        elif selector == "button[aria-label*='Review' i]":
            self.visible["button[aria-label*='Review' i]"] = False
            self.show("button[aria-label*='Submit application' i]")
        elif selector == "button[aria-label*='Submit application' i]":
            self.visible["button[aria-label*='Submit application' i]"] = False
            self.show("h3:has-text('Submitted')")

    async def goto(self, url: str, wait_until: str = "", timeout: int = 0) -> None:
        pass

    async def screenshot(self, path: str) -> None:
        self.shots.append(path)

    def locator(self, selector: str) -> FakeLocator:
        return FakeLocator(selector, self)


class FakeBrowserSession:
    """Minimal BrowserSession stand-in delegating to a FakePage."""

    def __init__(self) -> None:
        self.page = FakePage()

    async def navigate(self, url: str, page=None) -> FakePage:
        return self.page

    async def is_visible(self, selector: str, page=None, timeout_ms: int = 3000) -> bool:
        return page.is_selector_visible(selector)

    async def wait_for(self, selector: str, page=None, timeout_ms: int = 15000) -> None:
        if not page.is_selector_visible(selector):
            raise TimeoutError(f"selector {selector} not visible")

    async def click(self, selector: str, page=None) -> None:
        page.on_click(selector)

    async def screenshot(self, path, page=None):
        await page.screenshot(str(path))
        return path


def _profile() -> UserProfile:
    return UserProfile(
        profile_id="p_easy",
        personal_info=PersonalInfo(
            first_name="Aryan", last_name="Sharma", email="aryan@example.com", phone="+911234567890"
        ),
        skills=["Python"],
    )


class StubQA:
    """Deterministic QAEngine stand-in (no LLM) for hermetic saga tests."""

    async def answer_question(self, question: str, profile):
        from jobot.ai.qa_engine import AnswerResult, QuestionType

        q = question.lower()
        if "email" in q:
            answer, sensitive = profile.personal_info.email, False
        elif "phone" in q or "mobile" in q:
            answer, sensitive = profile.personal_info.phone, False
        else:
            answer, sensitive = "Grounded summary answer.", False
        return AnswerResult(
            question=question,
            answer=answer,
            question_type=QuestionType.PROFILE_DIRECT,
            is_grounded=True,
            confidence_score=1.0,
            requires_user_approval=sensitive,
        )


@pytest.mark.asyncio
async def test_easy_apply_happy_path():
    browser = FakeBrowserSession()
    saga = EasyApplySaga(
        browser, qa_engine=StubQA(), evidence_dir=Path(__import__("tempfile").mkdtemp())
    )
    result = await saga.run("https://linkedin.com/jobs/view/1", _profile())

    assert result.success is True
    assert result.status == "verify"
    assert len(result.evidence_shots) == 3
    assert result.unanswered_fields == []
    email_fills = [f for f in browser.page.fills if "input" in f[0]]
    assert any("aryan@example.com" in str(f[2]) for f in email_fills)


@pytest.mark.asyncio
async def test_easy_apply_missing_button():
    browser = FakeBrowserSession()
    browser.page.visible["button.jobs-apply-button"] = False
    saga = EasyApplySaga(
        browser, qa_engine=StubQA(), evidence_dir=Path(__import__("tempfile").mkdtemp())
    )
    result = await saga.run("https://linkedin.com/jobs/view/2", _profile())

    assert result.success is False
    assert "No Easy Apply button" in result.reason
    assert result.status == "open_posting"


@pytest.mark.asyncio
async def test_easy_apply_unknown_modal_state():
    browser = FakeBrowserSession()
    browser.page.visible["form"] = True
    browser.page.visible["button.jobs-apply-button"] = False
    saga = EasyApplySaga(
        browser, qa_engine=StubQA(), evidence_dir=Path(__import__("tempfile").mkdtemp())
    )
    result = await saga.run("https://linkedin.com/jobs/view/3", _profile())

    assert result.success is False
    assert "No Easy Apply button" in result.reason or "Unknown modal state" in result.reason


@pytest.mark.asyncio
async def test_easy_apply_respects_answer_overrides():
    browser = FakeBrowserSession()
    saga = EasyApplySaga(
        browser, qa_engine=StubQA(), evidence_dir=Path(__import__("tempfile").mkdtemp())
    )
    await saga.run(
        "https://linkedin.com/jobs/view/4",
        _profile(),
        answers={"email": "override@example.com"},
    )
    email_fills = [f for f in browser.page.fills if "input" in f[0] and f[1] == 0]
    assert any("override@example.com" in str(f[2]) for f in email_fills)
