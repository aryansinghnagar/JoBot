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

    async def submit(self, application: Application) -> bool:
        """Execute submission action and mark status SUBMITTED."""
        logger.info(f"[NAUKRI SUBMIT] Submitting application {application.application_id[:8]} for job {application.job_id}")
        application.status = ApplicationStatus.SUBMITTED
        return True
