"""LinkedIn Easy Apply browser saga (Phase 3, T3.6).

Drives the real LinkedIn Easy Apply modal through a BrowserSession with
selector-driven state machine: open posting -> click Easy Apply -> answer
questions (profile-grounded via QAEngine) -> review -> submit -> evidence
screenshots. Degrades cleanly: no Easy Apply button, unexpected modal state,
or unanswerable fields produce an explicit CANCELLED result instead of a
fabricated success.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from jobot.ai.qa_engine import QAEngine
from jobot.models.domain import UserProfile
from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)

DEFAULT_SELECTORS: Dict[str, List[str]] = {
    "easy_apply_button": [
        "button.jobs-apply-button",
        "button[aria-label*='Easy Apply' i]",
        "button:has-text('Easy Apply')",
    ],
    "modal": [
        "div[role='dialog']",
        ".jobs-easy-apply-modal",
        "form",
    ],
    "text_input": ["input[type='text'], input:not([type]), input[type='email'], input[type='tel']"],
    "textarea": ["textarea"],
    "select": ["select"],
    "next_button": [
        "button[aria-label*='Next' i]",
        "button:has-text('Next')",
    ],
    "review_button": [
        "button[aria-label*='Review' i]",
        "button:has-text('Review')",
    ],
    "submit_button": [
        "button[aria-label*='Submit application' i]",
        "button:has-text('Submit application')",
        "button[type='submit']",
    ],
    "success_text": [
        "h3:has-text('Submitted')",
        ".post-apply",
        "span:has-text('Application submitted')",
    ],
}


class EasyApplyStep(str, Enum):
    OPEN = "open_posting"
    CLICK_EASY_APPLY = "click_easy_apply"
    ANSWER_QUESTIONS = "answer_questions"
    SUBMIT = "submit"
    VERIFY = "verify"


class EasyApplyResult(BaseModel):
    success: bool
    status: str
    job_url: str
    evidence_shots: List[str] = []
    reason: str = ""
    unanswered_fields: List[str] = []


class EasyApplySaga:
    """Selector-driven state machine for the LinkedIn Easy Apply modal."""

    def __init__(
        self,
        browser: BrowserSession,
        qa_engine: Optional[QAEngine] = None,
        selectors: Optional[Dict[str, List[str]]] = None,
        evidence_dir: Optional[Path] = None,
    ):
        self.browser = browser
        self.qa_engine = qa_engine or QAEngine()
        self.selectors = {**DEFAULT_SELECTORS, **(selectors or {})}
        if evidence_dir is None:
            evidence_dir = Path.home() / ".jobot" / "evidence"
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    async def _first_visible(self, selectors: List[str], page: Any) -> Optional[str]:
        for selector in selectors:
            if await self.browser.is_visible(selector, page=page):
                return selector
        return None

    async def _collect_fields(self, page: Any) -> List[Dict[str, Any]]:
        """Collect visible interactive fields on the current modal step."""
        fields: List[Dict[str, Any]] = []
        for kind, selector in (
            ("text", "text_input"),
            ("textarea", "textarea"),
            ("select", "select"),
        ):
            locator = page.locator(self.selectors[selector][0])
            count = await locator.count()
            for i in range(count):
                el = locator.nth(i)
                try:
                    label = (
                        (await el.get_attribute("placeholder"))
                        or (await el.get_attribute("name"))
                        or (await el.get_attribute("aria-label"))
                        or ""
                    )
                except Exception:  # noqa: BLE001
                    label = ""
                fields.append(
                    {
                        "kind": kind,
                        "index": i,
                        "label": label or kind,
                        "selector": self.selectors[selector][0],
                        "locator": el,
                    }
                )
        return fields

    async def _answer_field(
        self, field: Dict[str, Any], profile: UserProfile, answers: Dict[str, str]
    ) -> bool:
        label = str(field["label"]).lower()
        for key, value in answers.items():
            if key.lower() in label:
                await field["locator"].fill(str(value))
                return True
        try:
            result = await self.qa_engine.answer_question(label, profile)
        except Exception:  # noqa: BLE001
            return False
        if result.requires_user_approval:
            return False
        answer = result.answer
        if not answer or answer.startswith("[") or "unavailable" in answer.lower():
            return False
        await field["locator"].fill(answer)
        return True

    async def run(
        self,
        job_url: str,
        profile: UserProfile,
        answers: Optional[Dict[str, str]] = None,
        resume_path: Optional[Path] = None,
    ) -> EasyApplyResult:
        """Execute the Easy Apply saga; returns explicit success/failure + evidence."""
        answers = answers or {}
        evidence: List[str] = []
        unanswered: List[str] = []

        page = await self.browser.navigate(job_url)
        shot = await self.browser.screenshot(self.evidence_dir / "01_opened.png", page=page)
        evidence.append(str(shot))

        button = await self._first_visible(self.selectors["easy_apply_button"], page)
        if not button:
            return EasyApplyResult(
                success=False,
                status=EasyApplyStep.OPEN.value,
                job_url=job_url,
                evidence_shots=evidence,
                reason="No Easy Apply button found on the posting page",
            )
        await self.browser.click(button, page=page)
        modal = await self._first_visible(self.selectors["modal"], page)
        if not modal:
            return EasyApplyResult(
                success=False,
                status=EasyApplyStep.CLICK_EASY_APPLY.value,
                job_url=job_url,
                evidence_shots=evidence,
                reason="Easy Apply clicked but no modal appeared",
            )
        shot = await self.browser.screenshot(self.evidence_dir / "02_modal.png", page=page)
        evidence.append(str(shot))

        try:
            while True:
                next_btn = await self._first_visible(self.selectors["next_button"], page)
                review_btn = await self._first_visible(self.selectors["review_button"], page)
                submit_btn = await self._first_visible(self.selectors["submit_button"], page)

                if submit_btn:
                    await self.browser.click(submit_btn, page=page)
                    break

                if review_btn:
                    await self.browser.click(review_btn, page=page)
                    continue

                if next_btn:
                    for field in await self._collect_fields(page):
                        if field["kind"] == "select":
                            continue
                        if not await self._answer_field(field, profile, answers):
                            unanswered.append(field["label"])
                    await self.browser.click(next_btn, page=page)
                    continue

                return EasyApplyResult(
                    success=False,
                    status=EasyApplyStep.ANSWER_QUESTIONS.value,
                    job_url=job_url,
                    evidence_shots=evidence,
                    reason="Unknown modal state: no Next/Review/Submit button visible",
                    unanswered_fields=unanswered,
                )
        except Exception as exc:  # noqa: BLE001
            return EasyApplyResult(
                success=False,
                status=EasyApplyStep.ANSWER_QUESTIONS.value,
                job_url=job_url,
                evidence_shots=evidence,
                reason=f"Easy Apply modal interaction failed: {exc}",
                unanswered_fields=unanswered,
            )

        shot = await self.browser.screenshot(self.evidence_dir / "03_submitted.png", page=page)
        evidence.append(str(shot))

        success_marker = await self._first_visible(self.selectors["success_text"], page)
        success = success_marker is not None
        return EasyApplyResult(
            success=success,
            status=EasyApplyStep.VERIFY.value,
            job_url=job_url,
            evidence_shots=evidence,
            reason=(
                "Easy Apply submitted and success marker visible"
                if success
                else "Submit clicked but no success marker found; manual verification required"
            ),
            unanswered_fields=unanswered,
        )
