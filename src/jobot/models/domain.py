from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TrustLevel(str, Enum):
    SUPERVISED = "supervised"
    GUIDED = "guided"
    AUTONOMOUS = "autonomous"
    TRUSTED = "trusted"


class ApplicationStatus(str, Enum):
    INTENT = "intent"
    PARSING = "parsing"
    PARSED = "parsed"
    MATCHING = "matching"
    MATCHED = "matched"
    FILLING = "filling"
    FILLED = "filled"
    REVIEWING = "reviewing"
    REVIEWED = "reviewed"
    PENDING_APPROVAL = "pending_approval"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    SUBMISSION_UNKNOWN = "submission_unknown"
    VERIFICATION_UNKNOWN = "verification_unknown"
    VERIFIED = "verified"
    OUTCOME_TRACKING = "outcome_tracking"
    INTERVIEW = "interview"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"
    FAILED = "failed"
    PAUSED = "paused"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    CIRCUIT_OPEN = "circuit_open"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    CANCELLED = "cancelled"


class PipelinePhase(str, Enum):
    PHASE_1_INTENT = "phase_1_intent"
    PHASE_2_PARSE = "phase_2_parse"
    PHASE_3_MATCH = "phase_3_match"
    PHASE_4_EXTRACT_QUESTIONS = "phase_4_extract_questions"
    PHASE_5_ANSWER_QUESTIONS = "phase_5_answer_questions"
    PHASE_6_FILL_FORM = "phase_6_fill_form"
    PHASE_7_VALIDATE_FILL = "phase_7_validate_fill"
    PHASE_8_GROUNDING_CHECK = "phase_8_grounding_check"
    PHASE_9_REVIEW = "phase_9_review"
    PHASE_10_APPROVAL = "phase_10_approval"
    PHASE_11_SUBMIT = "phase_11_submit"
    PHASE_12_VERIFY = "phase_12_verify"


class DoDResult(BaseModel):
    passed: bool
    reason: str = ""
    evidence_required: list[str] | None = None


class VerificationResult(BaseModel):
    success: bool
    confidence: float = 1.0
    confirmation_id: str | None = None
    evidence_snapshot_path: str | None = None
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# -------------------------------------------------------------------
# Candidate Profile Domain Models
# -------------------------------------------------------------------


class PersonalInfo(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location_city: str = ""
    location_state: str = ""
    location_country: str = "India"
    postal_code: str = ""
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class WorkExperience(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: str | None = None  # None = Present
    is_current: bool = False
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int | None = None
    gpa_or_percentage: str | None = None


class CompensationDetails(BaseModel):
    current_ctc_inr: float | None = None
    expected_ctc_inr: float | None = None
    minimum_annual_base_usd: float | None = None
    notice_period_days: int = 30
    negotiable_notice_period: bool = False


class UserProfile(BaseModel):
    profile_id: str = "default"
    version: int = 1
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    compensation: CompensationDetails = Field(default_factory=CompensationDetails)
    custom_qa_answers: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# -------------------------------------------------------------------
# Job Posting & Application Domain Models
# -------------------------------------------------------------------


class JobPosting(BaseModel):
    job_id: str
    site: str  # e.g., 'naukri', 'mock_ats'
    url: str
    title: str
    company: str
    location: str = ""
    experience_required: str = ""
    description: str = ""
    raw_html: str | None = None
    parsed_skills: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceItem(BaseModel):
    evidence_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    step_name: str
    screenshot_path: str | None = None
    form_data_snapshot: dict[str, Any] = Field(default_factory=dict)
    dom_html_path: str | None = None


class Application(BaseModel):
    application_id: str
    job_id: str
    site: str
    profile_id: str = "default"
    status: ApplicationStatus = ApplicationStatus.INTENT
    idempotency_key: str
    trust_level: TrustLevel = TrustLevel.SUPERVISED
    job_url: str | None = None
    form_values: dict[str, Any] = Field(default_factory=dict)
    unanswered_questions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
    responded_at: datetime | None = None
    outcome: str | None = None
    # Timestamp semantics split (MASTER_PLAN_EXPANDED.md §3.4): submission,
    # verification, and employer-response are distinct events and must never
    # share a single "updated" timestamp.
    submitted_at: datetime | None = None
    submission_verified_at: datetime | None = None
    first_employer_response_at: datetime | None = None
    current_outcome: str | None = None


# -------------------------------------------------------------------
# Task Graph & Goal Domain Models
# -------------------------------------------------------------------


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class Task(BaseModel):
    task_id: str
    goal_id: str
    title: str
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class Goal(BaseModel):
    goal_id: str
    title: str
    description: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CandidateFact(BaseModel):
    id: int | None = None
    profile_id: str = "default"
    fact_type: str  # skill | experience | education | credential | achievement
    fact_value: str
    source: str = "resume"  # resume | linkedin | user_asserted | inferred
    source_path: str | None = None
    confidence: float = 1.0
    verified: bool = False
    verified_at: datetime | None = None
    verified_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    superseded_by: int | None = None


class AnswerBankRecord(BaseModel):
    id: int | None = None
    profile_id: str = "default"
    question_hash: str
    question_text: str
    answer: str
    source: str = "user"  # profile | memory | llm | user
    used_count: int = 0
    last_used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FormFieldMemoryRecord(BaseModel):
    id: int | None = None
    profile_id: str = "default"
    adapter_id: str
    field_selector: str
    field_label: str | None = None
    field_type: str | None = None
    value: str
    confidence: float = 1.0
    last_used_at: datetime | None = None
