from jobot.failure.catalog import FailureMode
from jobot.memory.vector import VectorMemory
from jobot.obs.tracing import IncidentSeverity, TraceLogger
from jobot.stealth.circuit_breaker import CircuitBreaker


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    assert cb.get_state("naukri") == "CLOSED"

    # Record 1st failure
    cb.record_failure("naukri")
    assert cb.get_state("naukri") == "CLOSED"

    # Record 2nd failure -> Reaches threshold, opens circuit breaker
    cb.record_failure("naukri")
    assert cb.get_state("naukri") == "OPEN"

    # Success resets state
    cb.record_success("naukri")
    assert cb.get_state("naukri") == "CLOSED"


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


def test_vector_memory_integration():
    mem = VectorMemory(collection_name="dev2_test")
    mem.store_answer("dev_p1", "What is your primary language?", "Python", site="generic")
    results = mem.retrieve_similar("primary language", top_k=1)
    assert len(results) >= 1
    assert results[0]["answer"] == "Python"
