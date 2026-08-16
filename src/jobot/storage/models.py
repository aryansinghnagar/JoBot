from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationRecord(BaseModel):
    """Async ORM model for application persistence in SQLite."""

    id: Optional[int] = None
    application_id: str
    job_id: str
    site: str
    profile_id: str = "default"
    status: str
    idempotency_key: str
    trust_level: str = "supervised"
    form_values_json: str = "{}"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentRecord(BaseModel):
    """Async ORM model for tailored candidate documents."""

    id: Optional[int] = None
    application_id: str
    doc_type: str  # "resume", "cover_letter", "custom"
    content_path: str
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QAResponseRecord(BaseModel):
    """Async ORM model for application form questions and grounded answers."""

    id: Optional[int] = None
    application_id: str
    question: str
    answer: str
    confidence: float = 1.0
    sources_json: str = "[]"
    human_approved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobPostingRecord(BaseModel):
    """Async ORM model for discovered job requisitions."""

    job_id: str
    site: str
    url: str
    title: str
    company: str
    location: str = ""
    description: str = ""
    parsed_skills_json: str = "[]"
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
