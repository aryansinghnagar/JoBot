import pytest
from jobot.failure.catalog import CircuitBreaker, CircuitBreakerState, FailureMode
from jobot.memory.system import EightTierMemorySystem
from jobot.obs.tracing import IncidentSeverity, TraceLogger


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(site="naukri", failure_threshold=2, cooldown_seconds=0.1)

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # Record 1st failure
    cb.record_failure(FailureMode.NETWORK_TIMEOUT)
    assert cb.state == CircuitBreakerState.CLOSED

    # Record 2nd failure -> Reaches threshold, opens circuit breaker
    cb.record_failure(FailureMode.NETWORK_TIMEOUT)
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # Success resets state
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True


def test_trace_logger_and_incidents():
    logger = TraceLogger()

    span = logger.start_span("naukri_submit", {"job_id": "123"})
    assert span.name == "naukri_submit"
    logger.end_span(span)
    assert span.end_time is not None

    inc = logger.raise_incident(
        site="naukri",
        failure_mode=FailureMode.CAPTCHA_TRIGGERED,
        description="CAPTCHA requested during submit",
        severity=IncidentSeverity.HIGH,
    )
    assert inc.site == "naukri"
    assert inc.is_open is True


def test_eight_tier_memory_system():
    mem = EightTierMemorySystem()

    mem.set_working_memory("form_step", "filling_contact")
    assert mem.working_memory["form_step"] == "filling_contact"

    rec = mem.add_episodic_record("app_1", {"status": "submitted"})
    assert rec.tier == "episodic"
    assert len(mem.episodic_memory) == 1

    audit_rec = mem.add_audit_record("secret_accessed", {"vault": "master_key"})
    assert audit_rec.tier == "audit"
    assert len(mem.audit_memory) == 1
