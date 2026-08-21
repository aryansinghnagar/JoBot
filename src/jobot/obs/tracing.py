import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from jobot.failure.catalog import FailureMode
from jobot.security.pii_masker import PIIMasker


def _scrub_pii(data: Any, masker: PIIMasker) -> Any:
    """Recursively scrub PII patterns from strings, dicts, and lists."""
    if isinstance(data, str):
        masked, _ = masker.mask(data)
        return masked
    if isinstance(data, dict):
        return {k: _scrub_pii(v, masker) for k, v in data.items()}
    if isinstance(data, list):
        return [_scrub_pii(item, masker) for item in data]
    return data


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
    Persists trace spans to ~/.jobot/traces/<run_id>.jsonl with PII scrubbing.
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
        self.pii_masker = PIIMasker()

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> TraceSpan:
        cleaned_attrs = _scrub_pii(attributes or {}, self.pii_masker)
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            name=name,
            attributes=cleaned_attrs if isinstance(cleaned_attrs, dict) else {},
        )
        self.spans.append(span)
        return span

    def end_span(self, span: TraceSpan, status: str = "ok") -> None:
        span.end_time = datetime.now(UTC)
        span.attributes["status"] = status
        duration_ms = int((span.end_time - span.start_time).total_seconds() * 1000)
        span.attributes["duration_ms"] = duration_ms
        sanitized_attrs = _scrub_pii(span.attributes, self.pii_masker)

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
                        "attributes": sanitized_attrs,
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
        clean_desc, _ = self.pii_masker.mask(description)
        clean_action, _ = self.pii_masker.mask(recommended_action)
        inc = Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
            site=site,
            severity=severity,
            failure_mode=failure_mode,
            description=clean_desc,
            recommended_action=clean_action,
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
