import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from jobot.failure.catalog import FailureMode


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    is_open: bool = True
    recommended_action: str = ""


class TraceSpan(BaseModel):
    span_id: str
    name: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceLogger:
    """
    OpenTelemetry-compatible Trace & Incident Logger (Layer L).
    Persists trace spans to ~/.jobot/traces/<run_id>.jsonl.
    """

    def __init__(self, trace_dir: Path | None = None, run_id: str | None = None) -> None:
        if trace_dir is None:
            trace_dir = Path.home() / ".jobot" / "traces"
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = (
            run_id or f"run_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        )
        self.spans: list[TraceSpan] = []
        self.incidents: list[Incident] = []

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> TraceSpan:
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            name=name,
            attributes=attributes or {},
        )
        self.spans.append(span)
        return span

    def end_span(self, span: TraceSpan, status: str = "ok") -> None:
        span.end_time = datetime.now(UTC)
        span.attributes["status"] = status
        duration_ms = int((span.end_time - span.start_time).total_seconds() * 1000)
        span.attributes["duration_ms"] = duration_ms

        trace_file = self.trace_dir / f"{self.run_id}.jsonl"
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "span_id": span.span_id,
                        "run_id": self.run_id,
                        "name": span.name,
                        "start_time": span.start_time.isoformat(),
                        "end_time": span.end_time.isoformat(),
                        "duration_ms": duration_ms,
                        "attributes": span.attributes,
                    }
                )
                + "\n"
            )

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

    def list_traces(self) -> list[Path]:
        return sorted(list(self.trace_dir.glob("*.jsonl")))

    def get_trace_spans(self, run_id: str) -> list[dict[str, Any]]:
        trace_file = self.trace_dir / f"{run_id}.jsonl"
        if not trace_file.exists():
            return []
        spans = []
        with open(trace_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    spans.append(json.loads(line))
        return spans
