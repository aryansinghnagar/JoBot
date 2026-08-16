"""ApplyOrchestrator: saga-wrapped apply flow with dry-run and compensation (Phase 3, T3.4).

Composition: tailoring (T3.2/T3.3) + resume PDF/ATS scoring (T3.1) + the 12-phase
ASP pipeline for submission. The orchestrator adds durable saga checkpoints,
pre-submission grounding gates, compensating actions on failure, and a dry-run
mode that produces artifacts without submitting. It wraps the pipeline and never
reorders its phases (status contract preserved).
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from jobot.adapters import AdapterRegistry
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.asp.saga import ApplySaga, SagaStatus
from jobot.documents.ats import AtsScore, AtsScorer
from jobot.documents.cover import CoverLetterGenerator
from jobot.documents.pdf_exporter import ResumeExporter
from jobot.documents.tailor import DocumentTailor, TailoredDocumentResult
from jobot.llm.router import ModelRouter
from jobot.storage.db import DatabaseManager
from jobot.models.domain import Application, ApplicationStatus, JobPosting, UserProfile

logger = logging.getLogger(__name__)


class ApplyResult(BaseModel):
    saga_id: str
    job_id: str
    app_status: Optional[str] = None
    application_id: Optional[str] = None
    dry_run: bool
    artifacts: Dict[str, Any] = {}
    notes: List[str] = []


class ApplyOrchestrator:
    """Coordinates tailoring, artifact generation, and pipeline submission."""

    def __init__(
        self,
        db: DatabaseManager,
        router: Optional[ModelRouter] = None,
        artifact_dir: Optional[Path] = None,
    ):
        self.db = db
        self.router = router or ModelRouter()
        self.tailor = DocumentTailor(self.router)
        self.cover_generator = CoverLetterGenerator(self.router)
        self.exporter = ResumeExporter()
        self.scorer = AtsScorer()
        if artifact_dir is None:
            artifact_dir = Path.home() / ".jobot" / "resumes"
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    # -- artifact helpers ---------------------------------------------------

    def _experience_bullets(self, tailored: TailoredDocumentResult) -> Dict[str, List[str]]:
        bullets: Dict[str, List[str]] = {}
        for item in tailored.tailored_experience:
            key = f"{item.get('company', '')}|{item.get('title', '')}"
            bullets[key] = [str(b) for b in item.get("bullets", [])]
        return bullets

    def _export_artifacts(
        self,
        job: JobPosting,
        profile: UserProfile,
        tailored: TailoredDocumentResult,
        template: str,
        engine: Optional[str],
    ) -> Dict[str, Any]:
        job_dir = self.artifact_dir / f"{job.job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)
        pdf_path, ats = self.exporter.export_resume_pdf(
            profile,
            template=template,
            engine=engine,
            output_dir=job_dir,
            summary=tailored.tailored_summary,
            skills=tailored.highlighted_skills or None,
            experience_bullets=self._experience_bullets(tailored),
            scorer=self.scorer,
        )
        cover_path = job_dir / "cover_letter.txt"
        cover_path.write_text(tailored.cover_letter_text, encoding="utf-8")
        return {
            "resume_pdf": str(pdf_path),
            "resume_txt": str(pdf_path.with_suffix(".txt")),
            "cover_letter": str(cover_path),
            "ats_score": ats.score,
            "ats_passed": ats.passed,
            "is_truthful": tailored.is_truthful,
        }

    # -- public API ---------------------------------------------------------

    async def apply(
        self,
        job: JobPosting,
        profile: UserProfile,
        auto_approve: bool = False,
        dry_run: bool = False,
        resume_saga_id: Optional[str] = None,
        template: str = "default",
        engine: Optional[str] = None,
        tone: str = "classic",
        extra_prompt: str = "",
    ) -> ApplyResult:
        self.db.save_job_posting(job)

        saga = (
            ApplySaga.resume(self.db, resume_saga_id)
            if resume_saga_id
            else ApplySaga.start(self.db, job.job_id, profile.profile_id)
        )
        if saga is None:
            return ApplyResult(
                saga_id=resume_saga_id or "",
                job_id=job.job_id,
                dry_run=dry_run,
                notes=[f"Saga '{resume_saga_id}' not found"],
            )

        # --- tailoring (grounding gate) ------------------------------------
        try:
            tailored = await self.tailor.generate_tailored_materials(job, profile)
        except Exception as exc:  # noqa: BLE001
            saga.fail("tailoring", f"Tailoring failed: {exc}")
            return ApplyResult(
                saga_id=saga.saga_id,
                job_id=job.job_id,
                app_status=ApplicationStatus.FAILED.value,
                dry_run=dry_run,
                notes=[f"Tailoring failed: {exc}"],
            )
        saga.checkpoint("tailoring")

        if not tailored.is_truthful:
            saga.fail(
                "grounding",
                "Tailored materials contain ungrounded claims: "
                + "; ".join(tailored.truthfulness_notes),
            )
            return ApplyResult(
                saga_id=saga.saga_id,
                job_id=job.job_id,
                app_status=ApplicationStatus.REJECTED.value,
                dry_run=dry_run,
                notes=[f"Grounding gate failed: {tailored.truthfulness_notes}"],
            )
        saga.checkpoint("grounding")

        artifacts = self._export_artifacts(job, profile, tailored, template, engine)
        saga.checkpoint("artifacts")

        if dry_run:
            saga.complete()
            return ApplyResult(
                saga_id=saga.saga_id,
                job_id=job.job_id,
                dry_run=True,
                artifacts=artifacts,
                notes=["Dry run: no submission performed"],
            )

        # --- submission (wraps the 12-phase pipeline) -----------------------
        adapter = AdapterRegistry.get_adapter(job.site)
        pipeline = ApplicationSubmissionPipeline(
            adapter,
            self.db,
            extra_form_data={
                "_saga_id": saga.saga_id,
                "resume_path": artifacts["resume_pdf"],
                "cover_letter_text": tailored.cover_letter_text,
            },
        )
        app: Application = await pipeline.execute(job.url, profile, auto_approve=auto_approve)

        if app.status == ApplicationStatus.PENDING_APPROVAL:
            if app.form_values is None:
                app.form_values = {}
            app.form_values["resume_path"] = artifacts["resume_pdf"]
            app.form_values["_saga_id"] = saga.saga_id
            self.db.save_application(app)
            saga.checkpoint("approval_pending")
            return ApplyResult(
                saga_id=saga.saga_id,
                job_id=job.job_id,
                app_status=app.status.value,
                application_id=app.application_id,
                dry_run=False,
                artifacts=artifacts,
                notes=["Awaiting human approval before submission"],
            )

        if app.status in (ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED):
            saga.complete()
        else:
            self._compensate(saga, app)

        return ApplyResult(
            saga_id=saga.saga_id,
            job_id=job.job_id,
            app_status=app.status.value,
            application_id=app.application_id,
            dry_run=False,
            artifacts=artifacts,
            notes=[app.error_message] if app.error_message else [],
        )

    def _compensate(self, saga: ApplySaga, app: Application) -> None:
        """Compensating actions: never leave a stuck half-applied state."""
        if app.status == ApplicationStatus.CIRCUIT_OPEN:
            saga.fail("submit", app.error_message or "Circuit breaker open")
            saga.compensate("Circuit open; submission quarantined")
            return
        if app.status == ApplicationStatus.DUPLICATE_SKIPPED:
            saga.complete()
            return
        saga.fail("submit", app.error_message or f"Pipeline ended at {app.status.value}")
        if app.status not in (ApplicationStatus.REJECTED, ApplicationStatus.CANCELLED):
            app.status = ApplicationStatus.REJECTED
            self.db.save_application(app)
        saga.compensate(f"Submission failed: {app.error_message}")

    async def submit_approved(self, app: Application) -> ApplyResult:
        """Execute phases 11-12 for a PENDING_APPROVAL application."""
        adapter = AdapterRegistry.get_adapter(app.site)
        pipeline = ApplicationSubmissionPipeline(adapter, self.db)
        if app.form_values is None:
            app.form_values = {}
        submitted = await pipeline.submit_and_verify(app)

        saga_id = str((app.form_values or {}).get("_saga_id", ""))
        if saga_id:
            saga = ApplySaga.resume(self.db, saga_id)
            if submitted.status in (ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED):
                if saga:
                    saga.complete()
            elif saga:
                self._compensate(saga, submitted)

        return ApplyResult(
            saga_id=saga_id,
            job_id=app.job_id,
            app_status=submitted.status.value,
            dry_run=False,
            artifacts={},
            notes=[submitted.error_message] if submitted.error_message else [],
        )
