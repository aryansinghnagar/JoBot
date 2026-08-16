"""LLM provider strategy pattern: models, ABC, and shared HTTP helper.

Matches plan.md Chapter 6 (`jobot/llm/base.py`). HTTP providers share one
module-level helper so tests can monkeypatch a single call site.
"""

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Dict, List, Optional, cast
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from jobot.llm.pricing import PricingTable

logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str = "user"
    content: str = ""


class ToolSpec(BaseModel):
    name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)


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
    headers: Dict[str, str],
    payload: Dict[str, Any],
    timeout_s: float = 60.0,
) -> Dict[str, Any]:
    """POST JSON to a REST endpoint and return the parsed response body."""
    req = urllib.request.Request(
        url,
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        return cast(Dict[str, Any], json.loads(resp.read().decode("utf-8")))


def http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 5.0,
) -> Dict[str, Any]:
    """GET a JSON endpoint (used for cheap health probes)."""
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
        return cast(Dict[str, Any], json.loads(resp.read().decode("utf-8")))


def estimate_tokens(text: str) -> int:
    """Rough token estimate (whitespace split) for cost tracking."""
    return max(1, len(text.split()))


class LLMProvider(ABC):
    """Strategy interface for a concrete LLM provider (plan.md Chapter 6)."""

    name: str
    default_model: str
    pricing: Dict[str, ProviderPricing]

    def __init__(self, pricing_table: Optional["PricingTable"] = None) -> None:
        self.pricing: Dict[str, ProviderPricing] = {}
        self.key_lookup: Optional[Callable[[], Optional[str]]] = None
        if pricing_table is not None:
            self.pricing = pricing_table.providers.get(self.name, {})

    @abstractmethod
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]: ...

    @abstractmethod
    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    def _resolve_model(self, model: Optional[str]) -> str:
        return model or self.default_model

    def _resolve_pricing(self, model: Optional[str]) -> ProviderPricing:
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
