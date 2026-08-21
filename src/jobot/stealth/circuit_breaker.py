import asyncio
import logging
import socket
import ssl
import time
from collections.abc import Callable
from typing import Any, TypeVar
from urllib.parse import urlsplit

from jobot.obs.alerts import AlertDispatcher, AlertLevel

logger = logging.getLogger(__name__)
T = TypeVar("T")


# Module-level default TCP timeout for connection warmup. Kept short so a
# dead endpoint does not stall the warmup loop. The actual LLM/scrape
# calls use their own longer timeouts.
_WARMUP_TIMEOUT_S = 5.0


class CircuitOpenError(Exception):
    """Raised when an operation is attempted while circuit is OPEN."""

    pass


class CircuitBreaker:
    """
    Portal-level Circuit Breaker & Retry with Exponential Backoff (Layer 8).
    Prevents hammering failing portals and handles transient rate-limits gracefully.

    Phase P5: connection warmup. ``warmup(domain, ...)`` pre-establishes a
    TCP + TLS session to a known-good endpoint so the first real request
    does not pay the TLS handshake cost (~200ms). Warmup is idempotent and
    can be called on every cold start; subsequent calls are no-ops if the
    circuit is already CLOSED for that domain.

    Phase P5: circuit-breaker-aware request. ``cb_safe_request(url, ...)``
    checks the circuit state before issuing the request and records
    success / failure after — so callers do not have to wrap every HTTP
    call in a manual ``try/except`` + ``record_success``/``record_failure``
    dance.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        alert_dispatcher: AlertDispatcher | None = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.alert_dispatcher = alert_dispatcher or AlertDispatcher()

        self._failure_counts: dict[str, int] = {}
        self._circuit_state: dict[str, str] = {}  # "CLOSED", "OPEN", "HALF_OPEN"
        self._last_state_change: dict[str, float] = {}
        # Phase P5: track which domains have already been warmed up so
        # ``warmup`` is idempotent within the lifetime of the breaker.
        self._warmed_up: set[str] = set()

    def get_state(self, domain: str) -> str:
        state = self._circuit_state.get(domain, "CLOSED")
        if state == "OPEN":
            last_change = self._last_state_change.get(domain, 0.0)
            if time.time() - last_change > self.recovery_timeout:
                self._circuit_state[domain] = "HALF_OPEN"
                return "HALF_OPEN"
        return state

    def is_open(self, domain: str) -> bool:
        """Phase P5: convenience accessor — True if the circuit is OPEN
        (or just transitioned to HALF_OPEN). Use this from connection
        pools / request wrappers that want to skip dead endpoints."""
        return self.get_state(domain) in ("OPEN", "HALF_OPEN")

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
            self.alert_dispatcher.dispatch_alert(
                title=f"Circuit Breaker OPEN ({domain})",
                message=f"Circuit for '{domain}' tripped after {count} consecutive failures.",
                level=AlertLevel.CRITICAL,
            )

    # -- Phase P5: connection warmup --------------------------------------

    def warmup(self, domain: str, url: str | None = None, *, port: int = 443) -> bool:
        """Pre-establish a TCP + TLS session to ``domain``.

        Idempotent: returns True immediately if the domain was already
        warmed up in this breaker's lifetime AND the circuit is CLOSED.
        Otherwise opens a single TLS connection to ``domain:port``,
        records success/failure, and marks the domain as warmed-up.

        Returns True if the warmup succeeded (or was already warm).
        Returns False if the warmup failed — the caller MAY want to skip
        real requests to this domain until the circuit recovers.

        The ``url`` parameter, if provided, is used to extract the
        scheme + host + port (overriding ``port``). Use this when the
        real endpoint is on a non-default port.
        """
        if url is not None:
            parsed = urlsplit(url)
            host = (parsed.hostname or domain).lower()
            scheme = parsed.scheme.lower() or "https"
            port = parsed.port or (443 if scheme == "https" else 80)
            domain = host

        # Idempotent short-circuit: if we have already warmed up this
        # domain AND the circuit is still CLOSED, skip the probe.
        if domain in self._warmed_up and self.get_state(domain) == "CLOSED":
            return True

        # Refuse to warm up a domain whose circuit is OPEN — we want
        # the recovery timeout to fire before we retry.
        if self.get_state(domain) == "OPEN":
            return False

        try:
            # Open a single TCP connection and complete the TLS handshake.
            # We do not send any application data — the goal is just to
            # prime the OS-level DNS cache, the kernel's TCP connection
            # cache, and the TLS session cache (so the next request can
            # use TLS session resumption, cutting the handshake from
            # ~200ms to ~50ms).
            sock = socket.create_connection((domain, port), timeout=_WARMUP_TIMEOUT_S)
            try:
                if port == 443 or url is None or urlsplit(url).scheme == "https":
                    context = ssl.create_default_context()
                    # Enforce TLS 1.2+ (audit fix JOB-SEC-016, applied at the
                    # url_guard module level — replicate here for the warmup
                    # path which does not go through safe_urlopen).
                    context.minimum_version = ssl.TLSVersion.TLSv1_2
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        # Verify the cert actually validates — wrap_socket
                        # with the default context raises on cert errors.
                        ssock.do_handshake()
                else:
                    # Plain HTTP — TCP connect is enough.
                    pass
            finally:
                sock.close()
            self.record_success(domain)
            self._warmed_up.add(domain)
            logger.debug("circuit-breaker warmup OK for %s:%d", domain, port)
            return True
        except (OSError, ssl.SSLError, TimeoutError) as exc:
            logger.debug("circuit-breaker warmup failed for %s:%d: %s", domain, port, exc)
            self.record_failure(domain)
            return False

    async def warmup_async(self, domain: str, url: str | None = None) -> bool:
        """Async wrapper around ``warmup`` — runs the blocking TLS
        handshake on the default thread executor so the event loop is
        not frozen during warmup of multiple domains."""
        return await asyncio.to_thread(self.warmup, domain, url)

    def warmup_many(self, domains: list[str]) -> dict[str, bool]:
        """Warm up multiple domains in sequence. Returns a dict mapping
        each domain to its warmup result. Failures do not abort the
        loop — every domain is attempted exactly once."""
        results: dict[str, bool] = {}
        for domain in domains:
            results[domain] = self.warmup(domain)
        return results

    # -- Phase P5: circuit-breaker-aware request -------------------------

    def cb_safe_request(
        self,
        url: str,
        request_fn: Callable[..., Any],
        *args: Any,
        domain: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute ``request_fn(url, *args, **kwargs)`` with circuit-breaker
        gating. Before the call, checks the circuit state for ``domain``
        (extracted from ``url`` if not provided) and raises
        ``CircuitOpenError`` if OPEN. After the call, records success /
        failure. Does NOT retry — use ``execute_with_retry`` for retries.

        Phase P5: use this from connection pools that want circuit-breaker
        awareness without re-implementing the try/except boilerplate.
        """
        effective_domain = domain or self._domain_from_url(url)
        if self.is_open(effective_domain):
            raise CircuitOpenError(
                f"Circuit breaker is OPEN for domain '{effective_domain}'. Skipping request."
            )
        try:
            result = request_fn(url, *args, **kwargs)
            self.record_success(effective_domain)
            return result
        except (OSError, ConnectionError, TimeoutError, ssl.SSLError):
            self.record_failure(effective_domain)
            raise

    @staticmethod
    def _domain_from_url(url: str) -> str:
        parsed = urlsplit(url)
        return (parsed.hostname or "unknown").lower()

    async def execute_with_retry(
        self, domain: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        state = self.get_state(domain)
        if state == "OPEN":
            raise CircuitOpenError(
                f"Circuit breaker is OPEN for domain '{domain}'. Skipping request."
            )

        last_exception: Exception | None = None
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
