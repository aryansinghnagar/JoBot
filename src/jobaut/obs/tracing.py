import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jobaut.failure.catalog import FailureMode


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident(BaseModel):
    incident_id: str
    site: str
    severity: IncidentSeverity
    failure_mode: FailureMode
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    is_open: bool = True
    recommended_action: str = ""


class TraceSpan(BaseModel):
    span_id: str
    name: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class TraceLogger:
    """
    OpenTelemetry-compatible Trace & Incident Logger (Layer L).
    """

    def __init__(self) -> None:
        self.spans: List[TraceSpan] = []
        self.incidents: List[Incident] = []

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> TraceSpan:
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            name=name,
            attributes=attributes or {},
        )
        self.spans.append(span)
        return span

    def end_span(self, span: TraceSpan) -> None:
        span.end_time = datetime.now(timezone.utc)

    def raise_incident(
        self,
        site: str,
        failure_mode: FailureMode,
        description: str,
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
        recommended_action: str = "",
    ) -> Incident:
        inc = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
            site=site,
            severity=severity,
            failure_mode=failure_mode,
            description=description,
            recommended_action=recommended_action,
        )
        self.incidents.append(inc)
        return inc
