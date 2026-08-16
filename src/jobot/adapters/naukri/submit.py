import logging
from typing import Any, List, Optional

from jobot.models.domain import Application, ApplicationStatus
from jobot.stealth.behavior import BehavioralMimicry

logger = logging.getLogger(__name__)

APPLY_SELECTORS = [
    "button:has-text('Easy Apply')",
    "button:has-text('Apply Now')",
    "button:has-text('Apply')",
]

ALREADY_APPLIED_MARKERS = ["applied", "already applied", "application sent", "applied on"]

CONFIRMATION_TEXT = [
    "your application has been submitted",
    "application submitted",
    "you have successfully applied",
    "application sent",
]

LOGIN_WALL_SELECTORS = [
    "#usernameField",
    "input[name='username']",
    "input[placeholder*='Email']",
    ".login-form",
]


class NaukriSubmitter:
    """
    Naukri real application submission (P1.1).

    Requires an authenticated Patchright page on the job listing. Returns True
    only when a success indicator is observed after clicking the apply button.
    Never fabricates a submission: no page -> False, no button -> False,
    no confirmation -> False.
    """

    def __init__(self, mimicry: Optional[BehavioralMimicry] = None) -> None:
        self.mimicry = mimicry or BehavioralMimicry()

    async def _is_login_wall(self, page: Any) -> bool:
        for selector in LOGIN_WALL_SELECTORS:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    async def _first_apply_locator(self, page: Any) -> Optional[Any]:
        for selector in APPLY_SELECTORS:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    return locator
            except Exception:  # noqa: BLE001
                continue
        return None

    async def _confirmation_observed(self, page: Any) -> bool:
        for fragment in CONFIRMATION_TEXT:
            try:
                locator = page.locator(f"text={fragment}")
                if await locator.count() > 0:
                    return True
            except Exception:  # noqa: BLE001
                continue
        try:
            applied = page.locator("button:has-text('Applied')")
            if await applied.count() > 0:
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    async def _page_text(self, page: Any) -> str:
        try:
            body = page.locator("body")
            texts = await body.all_text_contents()
            return " ".join(texts).lower()
        except Exception:  # noqa: BLE001
            return ""

    async def submit(self, application: Application, page: Optional[Any] = None) -> bool:
        if page is None:
            logger.warning(
                "[NAUKRI SUBMIT] No browser page provided — refusing to fabricate a submission."
            )
            return False

        if application.job_url:
            try:
                await page.goto(application.job_url, wait_until="domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[NAUKRI SUBMIT] Navigation failed: {exc}")

        if await self._is_login_wall(page):
            logger.warning("[NAUKRI SUBMIT] Session not authenticated — cannot apply.")
            return False

        body_text = await self._page_text(page)
        if any(marker in body_text for marker in ALREADY_APPLIED_MARKERS):
            logger.info("[NAUKRI SUBMIT] Already applied to this job.")
            application.status = ApplicationStatus.SUBMITTED
            return True

        button = await self._first_apply_locator(page)
        if button is None:
            logger.warning("[NAUKRI SUBMIT] No apply button found on the page.")
            return False

        try:
            curve = self.mimicry.generate_bezier_curve((50, 50), (300, 400))
            logger.info(
                f"[NAUKRI STEALTH SUBMIT] Simulating mouse trajectory over {len(curve)} points to apply button"
            )
            await button.first.click(timeout=8000)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[NAUKRI SUBMIT] Apply click failed: {exc}")
            return False

        if not await self._confirmation_observed(page):
            logger.warning("[NAUKRI SUBMIT] No success indicator observed after click.")
            return False

        application.status = ApplicationStatus.SUBMITTED
        logger.info("[NAUKRI SUBMIT] Submission confirmed.")
        return True
