import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised when an operation is attempted while circuit is OPEN."""

    pass


class CircuitBreaker:
    """
    Portal-level Circuit Breaker & Retry with Exponential Backoff (Layer 8).
    Prevents hammering failing portals and handles transient rate-limits gracefully.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._failure_counts: Dict[str, int] = {}
        self._circuit_state: Dict[str, str] = {}  # "CLOSED", "OPEN", "HALF_OPEN"
        self._last_state_change: Dict[str, float] = {}

    def get_state(self, domain: str) -> str:
        state = self._circuit_state.get(domain, "CLOSED")
        if state == "OPEN":
            last_change = self._last_state_change.get(domain, 0.0)
            if time.time() - last_change > self.recovery_timeout:
                self._circuit_state[domain] = "HALF_OPEN"
                return "HALF_OPEN"
        return state

    def record_success(self, domain: str) -> None:
        self._failure_counts[domain] = 0
        self._circuit_state[domain] = "CLOSED"

    def record_failure(self, domain: str) -> None:
        count = self._failure_counts.get(domain, 0) + 1
        self._failure_counts[domain] = count
        if count >= self.failure_threshold:
            self._circuit_state[domain] = "OPEN"
            self._last_state_change[domain] = time.time()
            logger.warning(
                f"[CIRCUIT BREAKER] Circuit OPEN for domain '{domain}' after {count} failures."
            )

    async def execute_with_retry(
        self, domain: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        state = self.get_state(domain)
        if state == "OPEN":
            raise CircuitOpenError(
                f"Circuit breaker is OPEN for domain '{domain}'. Skipping request."
            )

        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                self.record_success(domain)
                return result
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    f"[RETRY] Attempt {attempt}/{self.max_retries} failed for '{domain}': {exc}"
                )
                if attempt < self.max_retries:
                    delay = self.backoff_factor ** (attempt - 1)
                    await asyncio.sleep(delay)

        self.record_failure(domain)
        if last_exception:
            raise last_exception
        raise RuntimeError(f"Operation failed after {self.max_retries} retries.")
