"""Tests for TraceLogger PII masking and telemetry safety."""

import json
from pathlib import Path

from jobot.failure.catalog import FailureMode
from jobot.obs.tracing import IncidentSeverity, TraceLogger


def test_trace_logger_pii_masking(tmp_path: Path):
    logger = TraceLogger(trace_dir=tmp_path, run_id="test_run_pii")

    span = logger.start_span(
        "apply_submission",
        attributes={
            "user_email": "candidate.secret@example.com",
            "phone": "+919876543210",
            "nested": {"contact": "reach out to recruiter@test.org"},
        },
    )
    logger.end_span(span, status="ok")

    trace_file = tmp_path / "test_run_pii.jsonl"
    assert trace_file.exists()
    content = trace_file.read_text(encoding="utf-8")
    data = json.loads(content.strip())

    # Raw emails/phones should be scrubbed
    assert "candidate.secret@example.com" not in content
    assert "+919876543210" not in content
    assert "recruiter@test.org" not in content
    assert "[EMAIL_0]" in data["attributes"]["user_email"]
    assert "[PHONE_0]" in data["attributes"]["phone"]


def test_trace_logger_incident_masking(tmp_path: Path):
    logger = TraceLogger(trace_dir=tmp_path, run_id="test_run_incident")
    inc = logger.raise_incident(
        site="naukri",
        failure_mode=FailureMode.GROUNDING_CHECK_FAILED,
        description="Failed on email john.doe@company.com with phone 9876543210",
        severity=IncidentSeverity.HIGH,
        recommended_action="Contact admin@company.com",
    )
    assert "john.doe@company.com" not in inc.description
    assert "[EMAIL_0]" in inc.description
    assert "admin@company.com" not in inc.recommended_action
