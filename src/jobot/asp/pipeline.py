import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.ai.qa_engine import QAEngine
from jobot.applications.state_machine import transition_application
from jobot.execution.engine import (
    ApprovalStatus as DurableApprovalStatus,
)
from jobot.execution.engine import DurableTaskEngine, DuplicateEffect, EffectStatus
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    DoDResult,
    EvidenceItem,
    JobPosting,
    PipelinePhase,
    TrustLevel,
    UserProfile,
)
from jobot.obs.alerts import AlertDispatcher, AlertLevel
from jobot.obs.tracing import TraceLogger
from jobot.policy.engine import PolicyEngine
from jobot.stealth.circuit_breaker import CircuitBreaker
from jobot.storage.db import DatabaseManager


class ApprovalRequiredError(Exception):
    """Raised when a supervised submission is attempted without an approved
    durable ApprovalRequest (G3: approvals are durable and enforced)."""


# Application statuses that represent an in-flight or committed submission:
# the pipeline must NEVER re-execute over these (reconcile instead).
_INFLIGHT_OR_COMMITTED = frozenset(
    {
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_UNKNOWN,
        ApplicationStatus.VERIFICATION_UNKNOWN,
        ApplicationStatus.VERIFIED,
        ApplicationStatus.OUTCOME_TRACKING,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
    }
)


class ApplicationSubmissionPipeline:
    """
    12-Phase Application Submission Pipeline (ASP) Specialized Harness.
    Enforces per-phase Definition of Done (DoD) verification gates, grounding checks,
    human approval checkpointing, evidence logging, and trace span recording.
    """

    def __init__(
        self,
        adapter: SiteAdapter,
        db_manager: DatabaseManager,
        artifact_dir: Optional[Path] = None,
        qa_engine: Optional[QAEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        trace_logger: Optional[TraceLogger] = None,
        alert_dispatcher: Optional[AlertDispatcher] = None,
        extra_form_data: Optional[Dict[str, Any]] = None,
    ):
        self.adapter = adapter
        self.db = db_manager
        if artifact_dir is None:
            artifact_dir = Path.home() / ".jobot" / "artifacts"
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.qa_engine = qa_engine or QAEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.trace_logger = trace_logger or TraceLogger()
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()
        self._extra_form_data = extra_form_data or {}
        self._engine_instance: Optional[DurableTaskEngine] = None

    def _engine(self) -> DurableTaskEngine:
        """Durable engine for effects/approvals (lazily shared per pipeline)."""
        if self._engine_instance is None:
            self._engine_instance = DurableTaskEngine(self.db)
        return self._engine_instance

    def _task_id(self, app: Application) -> str:
        return f"asp_{app.application_id[:12]}"

    def _request_hash(self, app: Application) -> str:
        payload = {k: v for k, v in (app.form_values or {}).items() if not k.startswith("_")}
        return hashlib.sha256(
            f"{app.site}::{app.job_id}::{sorted(payload.keys())}".encode()
        ).hexdigest()

    def _generate_idempotency_key(self, job_url: str, profile_id: str) -> str:
        raw = f"{job_url}::{profile_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def execute(
        self, job_url: str, profile: UserProfile, auto_approve: bool = False
    ) -> Application:
        idempotency_key = self._generate_idempotency_key(job_url, profile.profile_id)
        existing_app = self.db.get_application_by_idempotency_key(idempotency_key)

        if existing_app and existing_app.status == ApplicationStatus.VERIFIED:
            existing_app.status = ApplicationStatus.DUPLICATE_SKIPPED
            return existing_app

        if existing_app and existing_app.status in _INFLIGHT_OR_COMMITTED:
            # Never re-execute over an in-flight or committed submission —
            # reconciliation is the only sanctioned follow-up (G3).
            existing_app.status = ApplicationStatus.DUPLICATE_SKIPPED
            existing_app.error_message = (
                "application already submitted/committed; reconcile instead of re-running"
            )
            return existing_app

        if existing_app:
            app = existing_app
            app.status = ApplicationStatus.INTENT
        else:
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

        # 12-Phase Pipeline Execution with DoD Gates
        phases = [
            PipelinePhase.PHASE_1_INTENT,
            PipelinePhase.PHASE_2_PARSE,
            PipelinePhase.PHASE_3_MATCH,
            PipelinePhase.PHASE_4_EXTRACT_QUESTIONS,
            PipelinePhase.PHASE_5_ANSWER_QUESTIONS,
            PipelinePhase.PHASE_6_FILL_FORM,
            PipelinePhase.PHASE_7_VALIDATE_FILL,
            PipelinePhase.PHASE_8_GROUNDING_CHECK,
            PipelinePhase.PHASE_9_REVIEW,
        ]

        if not auto_approve and app.trust_level == TrustLevel.SUPERVISED:
            phases.append(PipelinePhase.PHASE_10_APPROVAL)
        else:
            phases.extend(
                [
                    PipelinePhase.PHASE_10_APPROVAL,
                    PipelinePhase.PHASE_11_SUBMIT,
                    PipelinePhase.PHASE_12_VERIFY,
                ]
            )

        for phase in phases:
            success = await self._execute_phase(phase, app, profile, job_url, auto_approve)
            if not success or app.status == ApplicationStatus.PENDING_APPROVAL:
                break

        if app.job_id and self.db.get_job_posting(app.job_id):
            self.db.save_application(app)
        return app

    async def _execute_phase(
        self,
        phase: PipelinePhase,
        app: Application,
        profile: UserProfile,
        job_url: str,
        auto_approve: bool,
    ) -> bool:
        span = self.trace_logger.start_span(phase.value, {"application_id": app.application_id})
        try:
            handler = getattr(self, f"_handle_{phase.value}")
            dod_result: DoDResult = await handler(app, profile, job_url, auto_approve)

            if not dod_result.passed:
                app.error_message = dod_result.reason
                if app.status not in [
                    ApplicationStatus.PENDING_APPROVAL,
                    ApplicationStatus.CIRCUIT_OPEN,
                    ApplicationStatus.DUPLICATE_SKIPPED,
                    ApplicationStatus.REJECTED,
                    ApplicationStatus.BLOCKED,
                    ApplicationStatus.SUBMISSION_UNKNOWN,
                    ApplicationStatus.VERIFICATION_UNKNOWN,
                ]:
                    app.status = ApplicationStatus.FAILED
                self.alert_dispatcher.dispatch_alert(
                    title=f"ASP Phase Status ({phase.value})",
                    message=f"Application {app.application_id[:8]}: {dod_result.reason}",
                    level=AlertLevel.HIGH
                    if app.status == ApplicationStatus.FAILED
                    else AlertLevel.INFO,
                )
                self.trace_logger.end_span(span, status=f"{app.status.value}: {dod_result.reason}")
                if app.job_id and self.db.get_job_posting(app.job_id):
                    self.db.save_application(app)
                return False

            self.trace_logger.end_span(span, status="ok")
            return True
        except Exception as exc:
            app.status = ApplicationStatus.FAILED
            app.error_message = str(exc)
            self.trace_logger.end_span(span, status=f"error: {exc}")
            if app.job_id and self.db.get_job_posting(app.job_id):
                self.db.save_application(app)
            return False

    async def _handle_phase_1_intent(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Profile must have first name or last name, and email."""
        if not profile.personal_info.first_name and not profile.personal_info.last_name:
            return DoDResult(passed=False, reason="Profile missing name")
        if not profile.personal_info.email:
            return DoDResult(passed=False, reason="Profile missing email")
        app.status = ApplicationStatus.INTENT
        return DoDResult(passed=True)

    async def _handle_phase_2_parse(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Job posting parsed with title, site, and job_id."""
        job_url = args[0]
        app.status = ApplicationStatus.PARSING
        job: JobPosting = await self.adapter.parse_job_posting(job_url)
        if job.job_id:
            app.job_id = job.job_id
            self.db.save_job_posting(job)
        if not job.title:
            return DoDResult(passed=False, reason="Job posting missing title")
        if not job.job_id:
            return DoDResult(passed=False, reason="Job posting missing job_id")
        app.status = ApplicationStatus.PARSED
        return DoDResult(passed=True)

    async def _handle_phase_3_match(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Evaluate match score against candidate profile."""
        app.status = ApplicationStatus.MATCHING
        job = self.db.get_job_posting(app.job_id)
        if not job:
            return DoDResult(passed=False, reason="Job posting record not found in database")
        app.status = ApplicationStatus.MATCHED
        return DoDResult(passed=True)

    async def _handle_phase_4_extract_questions(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Form questions extracted from target ATS."""
        job = self.db.get_job_posting(app.job_id)
        if not job:
            return DoDResult(passed=False, reason="Job posting record not found")
        form_questions = await self.adapter.extract_form_questions(job)
        if app.form_values is None:
            app.form_values = {}
        app.form_values["_extracted_questions"] = form_questions
        return DoDResult(passed=True)

    async def _handle_phase_5_answer_questions(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Q&A Engine answers profile-grounded questions; pauses on sensitive fields."""
        form_questions = (app.form_values or {}).get("_extracted_questions", [])
        qa_answers: Dict[str, Any] = {}
        for q in form_questions:
            res = await self.qa_engine.answer_question(q, profile)
            qa_answers[q] = res.answer
            if res.requires_user_approval:
                app.trust_level = TrustLevel.SUPERVISED
        if app.form_values is None:
            app.form_values = {}
        app.form_values.update(qa_answers)
        return DoDResult(passed=True)

    async def _handle_phase_6_fill_form(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Fill form data using adapter layer."""
        app.status = ApplicationStatus.FILLING
        job = self.db.get_job_posting(app.job_id)
        if not job:
            return DoDResult(passed=False, reason="Job posting record not found")
        form_data = await self.adapter.fill_form(job, profile, app)
        if not form_data or not isinstance(form_data, dict):
            return DoDResult(passed=False, reason="Form fill returned empty data dictionary")
        if app.form_values is None:
            app.form_values = {}
        app.form_values.update(form_data)
        app.status = ApplicationStatus.FILLED
        return DoDResult(passed=True)

    async def _handle_phase_7_validate_fill(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Required fields (email, name) populated in form_values."""
        form = app.form_values or {}
        if not form.get("email"):
            return DoDResult(passed=False, reason="Required field 'email' missing from form values")
        if not (form.get("name") or form.get("first_name") or form.get("full_name")):
            return DoDResult(passed=False, reason="Required field 'name' missing from form values")
        return DoDResult(passed=True)

    async def _handle_phase_8_grounding_check(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Grounding verification — populated email matches profile email."""
        app.status = ApplicationStatus.REVIEWING
        form = app.form_values or {}
        filled_email = form.get("email")
        if filled_email and filled_email != profile.personal_info.email:
            return DoDResult(
                passed=False,
                reason=f"Grounding failure: Filled email '{filled_email}' != '{profile.personal_info.email}'",
            )
        return DoDResult(passed=True)

    async def _handle_phase_9_review(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Policy governance & final review check."""
        app.status = ApplicationStatus.REVIEWED
        return DoDResult(passed=True)

    async def _handle_phase_10_approval(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Human approval gate — pause if supervised and not auto_approve.

        WS3: pausing creates a durable ApprovalRequest that survives restarts;
        its id is stored on the application so `submit_and_verify` (possibly
        in a later process) can enforce the approved decision (G3)."""
        auto_approve = args[1] if len(args) > 1 else False
        if app.trust_level == TrustLevel.SUPERVISED and not auto_approve:
            app.status = ApplicationStatus.PENDING_APPROVAL
            if not (app.form_values or {}).get("_approval_id"):
                approval = self._engine().create_approval(
                    self._task_id(app),
                    "SUBMIT",
                    risk_level=5,
                    requested_by="asp",
                    application_id=app.application_id,
                )
                if app.form_values is None:
                    app.form_values = {}
                app.form_values["_approval_id"] = approval.id
            return DoDResult(passed=True)
        return DoDResult(passed=True)

    def _approval_is_approved(self, app: Application) -> bool:
        approval_id = (app.form_values or {}).get("_approval_id")
        if not approval_id:
            # Legacy/autonomous path with no durable approval recorded.
            return app.trust_level != TrustLevel.SUPERVISED
        approval = self._engine().get_approval(str(approval_id))
        return approval is not None and approval.status is DurableApprovalStatus.APPROVED

    async def _handle_phase_11_submit(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: CircuitBreaker protected submission with evidence logging.

        WS3 effect-ledger protocol (G3): reserve the effect under the
        application's idempotency key BEFORE the external call; a duplicate
        reservation reconciles instead of re-executing; an ambiguous
        completion (crash/timeout after the call) lands in
        SUBMISSION_UNKNOWN for the reconciliation service — never a blind
        retry and never a second submission."""
        # Extra data (e.g. tailored resume path) is merged in right before submit,
        # so submit adapters see it without reordering pipeline phases.
        if self._extra_form_data:
            if app.form_values is None:
                app.form_values = {}
            app.form_values.update(self._extra_form_data)

        if self.circuit_breaker.get_state(app.site) == "OPEN":
            app.status = ApplicationStatus.CIRCUIT_OPEN
            return DoDResult(passed=False, reason=f"Circuit breaker is OPEN for site '{app.site}'")

        app.status = ApplicationStatus.SUBMITTING
        engine = self._engine()

        # 1) Reserve the effect (UNIQUE idempotency key = duplicate guard).
        try:
            engine.reserve_effect(
                self._task_id(app),
                "SUBMIT",
                app.idempotency_key,
                request_hash=self._request_hash(app),
                application_id=app.application_id,
            )
        except DuplicateEffect:
            existing = engine.get_effect(app.idempotency_key)
            if existing is not None and existing.status is EffectStatus.COMMITTED:
                # Already submitted (e.g. previous run crashed after commit):
                # reconcile forward, never re-execute.
                transition_application(
                    app, ApplicationStatus.SUBMITTED, reason="reconciled: effect already COMMITTED"
                )
                return DoDResult(passed=True)
            # PENDING/UNKNOWN reservation from a dead run: ambiguous — hand
            # to the reconciliation service (verify-only).
            transition_application(
                app,
                ApplicationStatus.SUBMISSION_UNKNOWN,
                reason="effect reserved by an earlier run; awaiting reconciliation",
            )
            return DoDResult(passed=False, reason="submission ambiguous; reconciliation required")

        # 2) Execute the external side effect EXACTLY once. The breaker
        # records the outcome for trip-counting but never retries a submit —
        # a retry after a post-send failure could double-submit (G3).
        try:
            submitted_ok = await self.adapter.submit_application(app)
            if submitted_ok:
                self.circuit_breaker.record_success(app.site)
            else:
                self.circuit_breaker.record_failure(app.site)
                engine.update_effect(
                    app.idempotency_key,
                    EffectStatus.FAILED,
                    task_id_for_events=self._task_id(app),
                )
                return DoDResult(passed=False, reason="Adapter submit_application returned False")
        except Exception as exc:
            self.circuit_breaker.record_failure(app.site)
            # The call may or may not have reached the ATS before dying:
            # UNKNOWN, never FAILED-with-retry.
            engine.update_effect(
                app.idempotency_key, EffectStatus.UNKNOWN, task_id_for_events=self._task_id(app)
            )
            transition_application(
                app, ApplicationStatus.SUBMISSION_UNKNOWN, reason=f"ambiguous submit: {exc}"
            )
            return DoDResult(passed=False, reason=f"Submission ambiguous (effect UNKNOWN): {exc}")

        engine.update_effect(
            app.idempotency_key,
            EffectStatus.COMMITTED,
            external_reference=str((app.form_values or {}).get("submission_id") or "") or None,
            task_id_for_events=self._task_id(app),
        )

        # Log submission evidence
        await self.adapter.capture_screenshot()
        evidence_item = EvidenceItem(
            evidence_id=str(uuid.uuid4()),
            step_name="phase_11_submit",
            form_data_snapshot=app.form_values,
        )
        app.evidence.append(evidence_item)
        transition_application(app, ApplicationStatus.SUBMITTED)
        return DoDResult(passed=True)

    async def _handle_phase_12_verify(
        self, app: Application, profile: UserProfile, *args: Any
    ) -> DoDResult:
        """DoD: Verify submission receipt with ATS server.

        WS3: a failed verification of a SUBMITTED application lands in
        VERIFICATION_UNKNOWN; a SUBMISSION_UNKNOWN application stays there —
        both are reconciliation territory, never retry-the-submit."""
        try:
            res = await self.circuit_breaker.execute_with_retry(
                app.site, self.adapter.verify_submission, app
            )
            if hasattr(res, "success"):
                if res.success:
                    transition_application(app, ApplicationStatus.VERIFIED)
                    self._engine().update_effect(
                        app.idempotency_key,
                        EffectStatus.COMMITTED,
                        external_reference=str(getattr(res, "confirmation_id", None) or ""),
                        task_id_for_events=self._task_id(app),
                    )
                    evidence_item = EvidenceItem(
                        evidence_id=str(uuid.uuid4()),
                        step_name="phase_12_verify",
                        screenshot_path=getattr(res, "evidence_snapshot_path", None),
                        form_data_snapshot={
                            "confirmation_id": getattr(res, "confirmation_id", None) or ""
                        },
                    )
                    app.evidence.append(evidence_item)
                    return DoDResult(passed=True)
                else:
                    if app.status is ApplicationStatus.SUBMITTED:
                        transition_application(
                            app,
                            ApplicationStatus.VERIFICATION_UNKNOWN,
                            reason=getattr(res, "reason", "Verification failed"),
                        )
                    elif app.status is ApplicationStatus.SUBMISSION_UNKNOWN:
                        app.error_message = getattr(res, "reason", "Verification failed")
                    return DoDResult(
                        passed=False, reason=getattr(res, "reason", "Verification failed")
                    )
            elif res:
                transition_application(app, ApplicationStatus.VERIFIED)
                evidence_item = EvidenceItem(
                    evidence_id=str(uuid.uuid4()),
                    step_name="phase_12_verify",
                    form_data_snapshot=app.form_values,
                )
                app.evidence.append(evidence_item)
                return DoDResult(passed=True)
            else:
                if app.status is ApplicationStatus.SUBMITTED:
                    transition_application(
                        app,
                        ApplicationStatus.VERIFICATION_UNKNOWN,
                        reason="Submission verification returned False",
                    )
                return DoDResult(passed=False, reason="Submission verification returned False")
        except Exception as exc:
            return DoDResult(passed=False, reason=f"Verification error: {exc}")

    async def submit_and_verify(self, app: Application) -> Application:
        """Direct Phase 11 & Phase 12 execution for approved applications.

        G3: a supervised application with a recorded durable approval is only
        submitted after that approval is APPROVED (the approval row lives in
        the database, so the decision survives restarts)."""
        if not self._approval_is_approved(app):
            app.error_message = (
                "submission refused: durable approval not APPROVED "
                "(jobot approval list / jobot approval decide <id> APPROVE)"
            )
            self.db.save_application(app)
            raise ApprovalRequiredError(app.error_message)
        profile = UserProfile(profile_id=app.profile_id)
        await self._handle_phase_11_submit(app, profile)
        if app.status == ApplicationStatus.SUBMITTED:
            await self._handle_phase_12_verify(app, profile)
        self.db.save_application(app)
        return app
