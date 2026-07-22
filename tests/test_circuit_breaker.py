import asyncio
import time
import pytest
from jobot.stealth.circuit_breaker import CircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_retry_success():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0, max_retries=3, backoff_factor=0.01)
    attempts = 0

    async def transient_func():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ValueError("Transient error")
        return "SUCCESS"

    result = await cb.execute_with_retry("test_domain", transient_func)
    assert result == "SUCCESS"
    assert attempts == 2
    assert cb.get_state("test_domain") == "CLOSED"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_threshold():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2, max_retries=1, backoff_factor=0.01)

    async def failing_func():
        raise RuntimeError("Persistent error")

    with pytest.raises(RuntimeError):
        await cb.execute_with_retry("bad_domain", failing_func)

    with pytest.raises(RuntimeError):
        await cb.execute_with_retry("bad_domain", failing_func)

    assert cb.get_state("bad_domain") == "OPEN"

    with pytest.raises(CircuitOpenError):
        await cb.execute_with_retry("bad_domain", failing_func)
