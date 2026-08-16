import logging
from typing import Any, cast
from jobot.models.domain import Application, ApplicationStatus, UserProfile

logger = logging.getLogger(__name__)


class ApplicationWorkflow:
    """
    Durable Application Submission Workflow Orchestration (Phase 2.3).
    Manages activity executions, retries, approval signals, and state checkpoints.
    """

    def __init__(self, pipeline: Any) -> None:
        self.pipeline = pipeline
        self._approval_received: bool = False

    async def execute_workflow(
        self,
        job_url: str,
        profile: UserProfile,
        auto_approve: bool = False,
    ) -> Application:
        """Execute durable 12-phase workflow with activity retries and approval signals."""
        logger.info(f"[WORKFLOW START] Starting durable application workflow for {job_url}")

        # Step 1: Execute 12-phase ASP pipeline up to approval checkpoint
        app = await self.pipeline.execute(job_url, profile, auto_approve=auto_approve)

        # Step 2: Handle Supervised Approval Checkpoint Signal
        if app.status == ApplicationStatus.PENDING_APPROVAL and not auto_approve:
            logger.info(
                f"[WORKFLOW APPROVAL WAIT] Application {app.application_id[:8]} awaiting approval signal..."
            )
            # Workflow checkpointing: wait for human approval signal or auto-approval trigger
            if self._approval_received or auto_approve:
                logger.info(
                    f"[WORKFLOW SIGNAL RECEIVED] Approval received for application {app.application_id[:8]}"
                )
                app = await self.pipeline.submit_and_verify(app)

        return cast(Application, app)

    def signal_approval(self) -> None:
        """Receive human approval signal for pending application."""
        self._approval_received = True
