import logging
from typing import Any

from jobot.models.domain import Application, VerificationResult

logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://www.naukri.com/mnjuser/myapplications"

ROW_SELECTORS = [
    ".application-row",
    ".job-tuple",
    "a[href*='/job/']",
    ".row1 a",
]

LOGIN_WALL_SELECTORS = [
    "#usernameField",
    "input[name='username']",
    "input[placeholder*='Email']",
]


class NaukriVerifier:
    """
    Naukri real submission verification (P1.2).

    Navigates to the candidate's applied-applications dashboard and checks the
    job actually appears in the list. Requires an authenticated page. Never
    fabricates a confirmation id.
    """

    async def _is_login_wall(self, page: Any) -> bool:
        for selector in LOGIN_WALL_SELECTORS:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    return True
            except Exception:  # noqa: BLE001, S112 — best-effort probe; selector failure is not actionable for callers, debug-logged below
                logger.debug("login-wall probe failed for selector %s", selector, exc_info=True)
                continue
        return False

    async def _application_rows(self, page: Any) -> list[str] | None:
        """Collect row texts from the dashboard; None if the list can't be read."""
        for selector in ROW_SELECTORS:
            try:
                locator = page.locator(selector)
                texts = await locator.all_text_contents()
                cleaned = [t.strip() for t in texts if t and t.strip()]
                if cleaned:
                    return cleaned
            except Exception:  # noqa: BLE001, S112 — best-effort probe across multiple selectors; the next selector is tried on failure
                logger.debug(
                    "application-row probe failed for selector %s", selector, exc_info=True
                )
                continue
        return None

    async def verify(
        self,
        application: Application,
        page: Any | None = None,
        job_title: str | None = None,
    ) -> VerificationResult:
        if page is None:
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason="No browser page provided — cannot verify against the Naukri dashboard.",
            )

        try:
            await page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
        except Exception as exc:  # noqa: BLE001
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason=f"Dashboard navigation failed: {exc}",
            )

        if await self._is_login_wall(page):
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason="Naukri session not authenticated — login required.",
            )

        rows = await self._application_rows(page)
        if rows is None:
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason="Could not parse the applied-applications list.",
            )

        needles = [application.job_id, application.job_url or ""]
        if job_title:
            needles.append(job_title)
        needles = [n.lower() for n in needles if n]

        matched = [row for row in rows if any(n in row.lower() for n in needles)]
        if matched:
            logger.info("[NAUKRI VERIFY] Application found in the applied list.")
            return VerificationResult(
                success=True,
                confidence=0.9,
                confirmation_id=application.job_id,
                reason="Job found in the Naukri applied-applications list.",
            )

        logger.warning("[NAUKRI VERIFY] Job not found in the applied list.")
        return VerificationResult(
            success=False,
            confidence=0.0,
            reason="Job not found in the applied-applications list.",
        )
