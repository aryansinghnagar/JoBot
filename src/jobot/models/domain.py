from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
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
    VERIFIED = "verified"
    FAILED = "failed"
    PAUSED = "paused"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    CIRCUIT_OPEN = "circuit_open"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    CANCELLED = "cancelled"


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
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: Optional[str] = None  # None = Present
    is_current: bool = False
    description: str = ""
    technologies: List[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: Optional[int] = None
    gpa_or_percentage: Optional[str] = None


class CompensationDetails(BaseModel):
    current_ctc_inr: Optional[float] = None
    expected_ctc_inr: Optional[float] = None
    notice_period_days: int = 30
    negotiable_notice_period: bool = False


class UserProfile(BaseModel):
    profile_id: str = "default"
    version: int = 1
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    experiences: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    compensation: CompensationDetails = Field(default_factory=CompensationDetails)
    custom_qa_answers: Dict[str, str] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    raw_html: Optional[str] = None
    parsed_skills: List[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceItem(BaseModel):
    evidence_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step_name: str
    screenshot_path: Optional[str] = None
    form_data_snapshot: Dict[str, Any] = Field(default_factory=dict)
    dom_html_path: Optional[str] = None


class Application(BaseModel):
    application_id: str
    job_id: str
    site: str
    profile_id: str = "default"
    status: ApplicationStatus = ApplicationStatus.INTENT
    idempotency_key: str
    trust_level: TrustLevel = TrustLevel.SUPERVISED
    form_values: Dict[str, Any] = Field(default_factory=dict)
    unanswered_questions: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


# -------------------------------------------------------------------
# Task Graph & Goal Domain Models
# -------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Task(BaseModel):
    task_id: str
    goal_id: str
    title: str
    description: str = ""
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class Goal(BaseModel):
    goal_id: str
    title: str
    description: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
