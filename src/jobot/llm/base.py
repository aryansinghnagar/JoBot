"""LLM provider strategy pattern: models, ABC, and shared HTTP helper.

Matches plan.md Chapter 6 (`jobot/llm/base.py`). HTTP providers share one
module-level helper so tests can monkeypatch a single call site.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any, Optional, cast

from pydantic import BaseModel, Field

from jobot.security.url_guard import safe_urlopen

if TYPE_CHECKING:
    from jobot.llm.pricing import PricingTable

logger = logging.getLogger(__name__)


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

    This is the synchronous helper that backs ``LLMProvider.complete``.
    Synchronous because it wraps ``urllib.request.urlopen`` (stdlib, blocking).
    Callers inside ``async`` coroutines should prefer ``http_post_json_async``
    so the event loop is not frozen for the duration of the LLM call
    (audit fix JOB-ARC-005 / JOB-ARC-004).
    """
    with safe_urlopen(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        timeout=timeout_s,
        method="POST",
    ) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode("utf-8")))


async def http_post_json_async(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    """Async wrapper around ``http_post_json``.

    Runs the blocking ``urllib`` POST on the default thread executor so the
    asyncio event loop stays free. This is the version that LLM providers
    should call from inside ``async def complete(...)`` — calling
    ``http_post_json`` directly freezes the loop for the full request window
    (audit fix JOB-ARC-005 / JOB-ARC-004).
    """
    return await asyncio.to_thread(http_post_json, url, headers, payload, timeout_s)


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
    """POST JSON with stream=True and asynchronously yield raw text lines."""
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
        except Exception as exc:  # noqa: BLE001
            loop.call_soon_threadsafe(q.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    fut = loop.run_in_executor(None, _reader)
    try:
        while True:
            item = await q.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        await fut


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
