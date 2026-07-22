import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from jobot.adapters.base import SiteAdapter
from jobot.models.domain import Application, ApplicationStatus, EvidenceItem, JobPosting, TrustLevel, UserProfile
from jobot.storage.db import DatabaseManager


class ApplicationSubmissionPipeline:
    """
    12-Phase Application Submission Pipeline (ASP) Specialized Harness.
    Executes form filling, deterministic profile grounding verification, human approval checkpointing,
    and evidence logging.
    """

    def __init__(self, adapter: SiteAdapter, db_manager: DatabaseManager, artifact_dir: Optional[Path] = None):
        self.adapter = adapter
        self.db = db_manager
        if artifact_dir is None:
            artifact_dir = Path.home() / ".jobot" / "artifacts"
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def _generate_idempotency_key(self, job_url: str, profile_id: str) -> str:
        raw = f"{job_url}::{profile_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def execute(
        self, job_url: str, profile: UserProfile, auto_approve: bool = False
    ) -> Application:
        # Phase 1: Intent
        idempotency_key = self._generate_idempotency_key(job_url, profile.profile_id)
        app_id = str(uuid.uuid4())
        app = Application(
            application_id=app_id,
            job_id="",
            site=self.adapter.site_name,
            profile_id=profile.profile_id,
            status=ApplicationStatus.INTENT,
            idempotency_key=idempotency_key,
            trust_level=TrustLevel.SUPERVISED if not auto_approve else TrustLevel.AUTONOMOUS,
        )

        # Phase 2 & 3: Job Parsing -> Parsed
        app.status = ApplicationStatus.PARSING
        job: JobPosting = await self.adapter.parse_job_posting(job_url)
        app.job_id = job.job_id
        self.db.save_job_posting(job)
        app.status = ApplicationStatus.PARSED

        # Phase 4 & 5: Matching -> Matched
        app.status = ApplicationStatus.MATCHING
        # Profile matching logic (score calculation)
        app.status = ApplicationStatus.MATCHED

        # Phase 6 & 7: Form Filling -> Filled
        app.status = ApplicationStatus.FILLING
        form_data = await self.adapter.fill_form(job, profile, app)
        app.status = ApplicationStatus.FILLED

        # Phase 8 & 9: Review & Grounding Check -> Reviewed
        app.status = ApplicationStatus.REVIEWING
        # Deterministic Grounding Check: Ensure filled email matches candidate profile email
        if form_data.get("email") and form_data.get("email") != profile.personal_info.email:
            app.status = ApplicationStatus.FAILED
            app.error_message = "Grounding failure: Filled email does not match profile email."
            self.db.save_application(app)
            return app
        app.status = ApplicationStatus.REVIEWED

        # Phase 10: Approval Gate
        if app.trust_level == TrustLevel.SUPERVISED and not auto_approve:
            app.status = ApplicationStatus.PENDING_APPROVAL
            self.db.save_application(app)
            # Pauses for user approval in CLI / GUI
            return app

        # Phase 11 & 12
        if auto_approve:
            return await self.submit_and_verify(app)
        else:
            app.status = ApplicationStatus.PENDING_APPROVAL
            self.db.save_application(app)
            return app

    async def submit_and_verify(self, app: Application) -> Application:
        """Execute Phase 11 (submit) and Phase 12 (verify) with full evidence capture."""
        app.status = ApplicationStatus.SUBMITTING
        submitted_ok = await self.adapter.submit_application(app)
        if not submitted_ok:
            app.status = ApplicationStatus.FAILED
            app.error_message = "Submission failed at adapter layer."
            self.db.save_application(app)
            return app

        verified_ok = await self.adapter.verify_submission(app)
        if verified_ok:
            app.status = ApplicationStatus.VERIFIED
            evidence_item = EvidenceItem(
                evidence_id=str(uuid.uuid4()),
                step_name="submission_verified",
                form_data_snapshot=app.form_values,
            )
            app.evidence.append(evidence_item)
        else:
            app.status = ApplicationStatus.FAILED
            app.error_message = "Submission verification failed."

        app.updated_at = datetime.now(timezone.utc)
        self.db.save_application(app)
        return app
