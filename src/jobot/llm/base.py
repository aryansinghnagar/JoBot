"""LLM provider strategy pattern: models, ABC, and shared HTTP helper.

Matches plan.md Chapter 6 (`jobot/llm/base.py`). HTTP providers share one
module-level helper so tests can monkeypatch a single call site.

Phase C2 / P1: the async HTTP path is now backed by a module-level
``httpx.AsyncClient`` connection pool. The pool is lazily created on the
first async request and reused for every subsequent call so the TCP +
TLS handshake cost is amortised across requests (saves ~200ms per LLM
call). The sync ``http_post_json`` / ``http_get_json`` helpers remain
urllib-based for non-async call sites (tests, sync scripts).
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any, Optional, cast

from pydantic import BaseModel, Field

from jobot.security.url_guard import _TLS_CONTEXT, safe_urlopen, validate_fetch_url

if TYPE_CHECKING:
    from jobot.llm.pricing import PricingTable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase C2 / P1: module-level httpx.AsyncClient connection pool.
#
# Lazy-initialised on first call to avoid requiring an event loop at import
# time. The pool reuses TCP connections + TLS sessions across requests so
# repeated LLM calls to the same provider (api.openai.com, etc.) skip the
# ~200ms TLS handshake after the first call.
# ---------------------------------------------------------------------------

try:
    import httpx  # Phase C2/P1: pooled async HTTP client

    _HTTPX_CLIENT: Optional["httpx.AsyncClient"] = None
    _HTTPX_POOL_LIMITS = httpx.Limits(
        max_connections=100,  # across all hosts
        max_keepalive_connections=20,  # idle keep-alive sockets held open
        keepalive_expiry=30.0,  # seconds before idle keep-alive sockets close
    )

    def _get_httpx_client() -> "httpx.AsyncClient":
        """Return the module-level AsyncClient, creating it on first call.

        The client is configured with:
        * our ``_TLS_CONTEXT`` (forces TLS 1.2+, audit fix JOB-SEC-016);
        * a generous connection pool (100 max conns, 20 keep-alive);
        * a 60s default timeout — callers can override per-request.
        """
        global _HTTPX_CLIENT
        if _HTTPX_CLIENT is None or _HTTPX_CLIENT.is_closed:
            _HTTPX_CLIENT = httpx.AsyncClient(
                verify=_TLS_CONTEXT,  # type: ignore[arg-type]
                limits=_HTTPX_POOL_LIMITS,
                timeout=httpx.Timeout(60.0, connect=10.0),
                follow_redirects=True,
            )
        return _HTTPX_CLIENT

    async def _close_httpx_client() -> None:
        """Close the pool. Called from atexit / test teardown to release
        keep-alive sockets cleanly. Safe to call multiple times."""
        global _HTTPX_CLIENT
        if _HTTPX_CLIENT is not None and not _HTTPX_CLIENT.is_closed:
            await _HTTPX_CLIENT.aclose()
        _HTTPX_CLIENT = None

    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover — httpx is a hard dependency as of 0.2.x
    _HTTPX_AVAILABLE = False
    _HTTPX_CLIENT = None

    def _get_httpx_client() -> Any:  # type: ignore[no-redef]
        raise RuntimeError(
            "httpx is not installed — install with `pip install httpx>=0.27.0`"
        )

    async def _close_httpx_client() -> None:  # type: ignore[no-redef]
        pass


class Message(BaseModel):
    role: str = "user"
    content: str = ""


class ToolSpec(BaseModel):
    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    provider: str
    model: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


class ProviderPricing(BaseModel):
    input_per_1k: float = 0.0
    output_per_1k: float = 0.0
    max_tokens: int = 4096


def http_post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """POST JSON to a REST endpoint and return the parsed response body.

    This is the synchronous helper that backs sync ``LLMProvider.complete``
    call sites and the test suite. Synchronous because it wraps
    ``urllib.request.urlopen`` (stdlib, blocking). Callers inside ``async``
    coroutines should prefer ``http_post_json_async`` so the event loop is
    not frozen for the duration of the LLM call (audit fix JOB-ARC-005 /
    JOB-ARC-004) AND so they benefit from the module-level httpx connection
    pool (Phase P1).
    """
    with safe_urlopen(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        timeout=timeout_s,
        method="POST",
    ) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


async def safe_urlopen_async(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    method: str = "GET",
    allow_private_hosts: bool = False,
) -> "httpx.Response":
    """Async validate-then-fetch: the httpx-backed counterpart of
    ``safe_urlopen`` (Phase C2 / JOB-ARC-004).

    Runs the same SSRF guard (``validate_fetch_url``) before issuing the
    request, and reuses the module-level ``httpx.AsyncClient`` connection
    pool so repeated calls to the same host skip the TCP + TLS handshake
    (Phase P1 — saves ~200ms per LLM call after the first).

    Returns the ``httpx.Response`` (callers can access ``.json()``,
    ``.text``, or iterate ``.aiter_lines()`` for streaming).
    """
    validated = validate_fetch_url(url, allow_private_hosts=allow_private_hosts)
    client = _get_httpx_client()
    request_method = method.upper() if method else "GET"
    response = await client.request(
        request_method,
        validated,
        content=data,
        headers=headers or {},
        timeout=timeout,
    )
    response.raise_for_status()
    return response


async def http_post_json_async(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """Async POST JSON: uses the module-level httpx.AsyncClient pool
    (Phase C2 / P1, JOB-ARC-004).

    Falls back to ``asyncio.to_thread(http_post_json, ...)`` (the urllib
    path) if httpx is not importable — keeps the sidecar functional in
    minimal environments that have not yet picked up the new dependency.
    """
    if not _HTTPX_AVAILABLE:
        return await asyncio.to_thread(http_post_json, url, headers, payload, timeout_s)
    response = await safe_urlopen_async(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        timeout=timeout_s,
        method="POST",
    )
    return cast(dict[str, Any], response.json())


def http_get_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """GET a JSON endpoint (used for cheap health probes)."""
    with safe_urlopen(url, headers=headers or {}, timeout=timeout_s) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


async def http_post_sse_async(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> AsyncIterator[str]:
    """POST JSON with stream=True and asynchronously yield raw text lines
    (Phase C2 / P1: now backed by httpx streaming instead of the
    thread-executor bridge)."""
    if not _HTTPX_AVAILABLE:
        # Legacy urllib-backed path: kept for minimal environments without
        # httpx. Uses the thread-executor bridge.
        loop = asyncio.get_running_loop()
        q: asyncio.Queue[Any | None] = asyncio.Queue()

        def _reader() -> None:
            try:
                with safe_urlopen(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    timeout=timeout_s,
                    method="POST",
                ) as resp:
                    for line in resp:
                        text = line.decode("utf-8").strip()
                        if text:
                            loop.call_soon_threadsafe(q.put_nowait, text)
            except (OSError, ConnectionError, TimeoutError, json.JSONDecodeError) as exc:
                loop.call_soon_threadsafe(q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        fut = loop.run_in_executor(None, _reader)
        try:
            while True:
                item = await q.get()
                if item is None:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            await fut
        return

    # httpx streaming path — reuses the module-level pool.
    validated = validate_fetch_url(url)
    client = _get_httpx_client()
    async with client.stream(
        "POST",
        validated,
        content=json.dumps(payload).encode("utf-8"),
        headers=headers,
        timeout=timeout_s,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            text = line.strip()
            if text:
                yield text


def estimate_tokens(text: str) -> int:
    """Token estimate (~4 chars per token) for robust budget/cost tracking."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


class LLMProvider(ABC):
    """Strategy interface for a concrete LLM provider (plan.md Chapter 6)."""

    name: str
    default_model: str
    pricing: dict[str, ProviderPricing]

    def __init__(self, pricing_table: Optional["PricingTable"] = None) -> None:
        self.pricing: dict[str, ProviderPricing] = {}
        self.key_lookup: Callable[[], str | None] | None = None
        if pricing_table is not None:
            self.pricing = pricing_table.providers.get(self.name, {})

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[ToolSpec] | None = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse: ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[ToolSpec] | None = None,
        timeout_s: float = 60.0,
        **kwargs: Any,
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: str | None = None
    ) -> float: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    def _resolve_model(self, model: str | None) -> str:
        return model or self.default_model

    def _resolve_pricing(self, model: str | None) -> ProviderPricing:
        key = self._resolve_model(model)
        if key in self.pricing:
            return self.pricing[key]
        if self.default_model in self.pricing:
            return self.pricing[self.default_model]
        return ProviderPricing()

    async def _run_in_thread(self, fn: Any, *args: Any) -> Any:
        """Run a blocking SDK call off the event loop (boto3 is sync)."""
        return await asyncio.to_thread(fn, *args)

    def _timed(self, start: float) -> float:
        return round((time.monotonic() - start) * 1000.0, 1)
