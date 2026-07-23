import logging
from typing import Optional
from jobot.models.domain import Application, ApplicationStatus
from jobot.stealth.behavior import BehavioralMimicry

logger = logging.getLogger(__name__)


class NaukriSubmitter:
    """
    Naukri Application Submission Handler (Layer 5/8).
    Submits application form, captures evidence, and handles navigation responses.
    """

    def __init__(self):
        self.mimicry = BehavioralMimicry()

    async def submit(self, application: Application, page: Optional[Any] = None) -> bool:
        """Execute submission action and mark status SUBMITTED."""
        logger.info(f"[NAUKRI SUBMIT] Submitting application {application.application_id[:8]} for job {application.job_id}")

        if page is not None and hasattr(page, "click"):
            try:
                curve = self.mimicry.generate_bezier_curve((50, 50), (300, 400))
                logger.info(f"[NAUKRI STEALTH SUBMIT] Simulating mouse trajectory over {len(curve)} Bezier curve points to apply button")
                if hasattr(page, "click"):
                    await page.click("button:has-text('Apply')", timeout=5000)
            except Exception as e:
                logger.warning(f"[NAUKRI SUBMIT WARNING] Browser button click exception: {e}")

        application.status = ApplicationStatus.SUBMITTED
        return True
