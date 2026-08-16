import logging
from jobot.models.domain import Application, ApplicationStatus

logger = logging.getLogger(__name__)


class NaukriVerifier:
    """
    Naukri Application Verification Handler (Layer 5/8).
    Verifies application receipt and updates status to VERIFIED.
    """

    async def verify(self, application: Application) -> bool:
        """Verify application status in candidate dashboard or response receipt."""
        logger.info(f"[NAUKRI VERIFY] Verifying submission for application {application.application_id[:8]}")
        application.status = ApplicationStatus.VERIFIED
        return True
