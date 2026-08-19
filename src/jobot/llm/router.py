"""ModelRouter v2: strategy-based, cost-aware routing with fallback chains.

Frozen public contract (docs/contracts.md) preserved: `generate_text(prompt,
system_prompt=None, fallback_chain=None)` keeps its signature and semantics
(returns `[LLM_UNAVAILABLE] ...` degradation text when nothing works).
Task overrides and persisted daily spend are additive.
"""

import json
import logging
import os
from collections.abc import AsyncIterator, Callable
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from jobot.llm.base import LLMProvider, LLMResponse, Message
from jobot.llm.pricing import PricingTable
from jobot.llm.providers import PROVIDER_REGISTRY
from jobot.secrets import get_secret

logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_CHAIN = ["gemini", "openai", "anthropic", "ollama"]
DEFAULT_DAILY_BUDGET_USD = 5.0
DEGRADATION_TEXT = (
    "[LLM_UNAVAILABLE] Information from profile facts: Please refer to candidate profile."
)


class ModelProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    TOGETHER = "together"
    OLLAMA = "ollama"
    VLLM = "vllm"
    MISTRAL = "mistral"
    COHERE = "cohere"
    BEDROCK = "bedrock"
    VERTEX = "vertex"


class ModelCallMetrics(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


def _default_spend_path() -> Path:
    return Path.home() / ".jobot" / "data" / "llm_spend.json"


class ModelRouter:
    """Provider-neutral LLM router (plan.md Chapter 6, ModelRouter v2)."""

    def __init__(
        self,
        primary_provider: ModelProvider = ModelProvider.GEMINI,
        pricing_table: PricingTable | None = None,
        spend_path: Path | None = None,
        daily_budget_usd: float | None = None,
    ) -> None:
        self._load_dotenv()
        self.pricing = pricing_table or PricingTable()
        self.spend_path = spend_path or _default_spend_path()
        self.daily_budget_usd = (
            daily_budget_usd if daily_budget_usd is not None else DEFAULT_DAILY_BUDGET_USD
        )
        self.primary_provider = primary_provider
        self.metrics_history: list[ModelCallMetrics] = []
        self._providers: dict[str, LLMProvider] = {}
        self._spend: dict[str, float] = self._load_spend()

    # -- dotenv + keyring ---------------------------------------------------

    def _load_dotenv(self) -> None:
        env_path = Path.home() / ".jobot" / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if "#" in v and not (
                            (v.startswith('"') and v.endswith('"'))
                            or (v.startswith("'") and v.endswith("'"))
                        ):
                            v = v.split("#", 1)[0].strip()
                        if len(v) >= 2 and (
                            (v.startswith('"') and v.endswith('"'))
                            or (v.startswith("'") and v.endswith("'"))
                        ):
                            v = v[1:-1]
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to read .env at %s: %s", env_path, exc)

    def _api_key_for(self, provider_name: str) -> str | None:
        env_name = f"{provider_name.upper()}_API_KEY"
        key = os.getenv(env_name)
        if key:
            return key
        return get_secret(f"llm.api_key.{provider_name}")

    # -- spend persistence --------------------------------------------------

    def _load_spend(self) -> dict[str, float]:
        if not self.spend_path.exists():
            return {}
        try:
            raw = json.loads(self.spend_path.read_text(encoding="utf-8"))
            return {str(k): float(v) for k, v in raw.items() if isinstance(v, (int, float))}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load LLM spend file %s: %s", self.spend_path, exc)
            return {}

    def _save_spend(self) -> None:
        try:
            self.spend_path.parent.mkdir(parents=True, exist_ok=True)
            self.spend_path.write_text(json.dumps(self._spend, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist LLM spend to %s: %s", self.spend_path, exc)

    @property
    def today_key(self) -> str:
        return date.today().isoformat()

    @property
    def current_spent_usd(self) -> float:
        return self._spend.get(self.today_key, 0.0)

    def _record_spend(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self._spend[self.today_key] = self.current_spent_usd + amount
        self._save_spend()

    # -- provider access ----------------------------------------------------

    def get_provider(self, provider_name: str) -> LLMProvider | None:
        name = provider_name.lower()
        if name in self._providers:
            return self._providers[name]
        factory = PROVIDER_REGISTRY.get(name)
        if factory is None:
            logger.warning("Unknown LLM provider '%s'", name)
            return None
        try:
            instance = factory(self.pricing) if isinstance(factory, type) else factory()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to instantiate provider '%s': %s", name, exc)
            return None
        instance.key_lookup = self._key_lookup_for(name)
        self._providers[name] = instance
        return instance

    def _key_lookup_for(self, name: str) -> Callable[[], str | None]:
        return lambda: self._api_key_for(name)

    # -- cost awareness -----------------------------------------------------

    def _is_local(self, provider: LLMProvider) -> bool:
        return provider.name in ("ollama", "vllm")

    def _budget_exhausted(self, provider: LLMProvider) -> bool:
        if self._is_local(provider):
            return False
        return self.current_spent_usd >= self.daily_budget_usd

    # -- task overrides -----------------------------------------------------

    def _resolve_task_override(self, task: str | None) -> dict[str, Any] | None:
        if not task:
            return None
        from jobot.config.profile import load_llm_settings  # local import avoids cycle

        override = load_llm_settings().task_overrides.get(task)
        return override.model_dump() if override else None

    def _resolve_chain(self, fallback_chain: list[Any] | None, task: str | None) -> list[str]:
        override = self._resolve_task_override(task)
        chain = [
            str(p.value if isinstance(p, ModelProvider) else p) for p in (fallback_chain or [])
        ]
        if not chain:
            chain = list(DEFAULT_FALLBACK_CHAIN)
        if override and override.get("provider"):
            provider = str(override["provider"])
            chain = [provider] + [p for p in chain if p != provider]
        return chain

    # -- public API ---------------------------------------------------------

    async def complete(
        self,
        messages: list[Message],
        provider: str | None = None,
        model: str | None = None,
        task: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        """Strategy-level call to a single provider (respects budget + keyring)."""
        override = self._resolve_task_override(task)
        provider_name = provider or self.primary_provider.value
        if override and override.get("provider"):
            provider_name = str(override["provider"])
        model = model or (override or {}).get("model")
        inst = self.get_provider(provider_name)
        if inst is None:
            raise ValueError(f"Provider '{provider_name}' is not available")
        if self._budget_exhausted(inst):
            raise RuntimeError(f"Daily LLM budget (${self.daily_budget_usd:.2f}) exhausted")
        response = await inst.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        )
        self.metrics_history.append(
            ModelCallMetrics(
                provider=response.provider,
                model=response.model,
                prompt_tokens=response.input_tokens,
                completion_tokens=response.output_tokens,
                estimated_cost_usd=response.estimated_cost_usd,
                latency_ms=response.latency_ms,
            )
        )
        self._record_spend(response.estimated_cost_usd)
        return response

    async def stream(
        self,
        messages: list[Message],
        provider: str | None = None,
        model: str | None = None,
        task: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout_s: float = 60.0,
    ) -> AsyncIterator[str]:
        """Strategy-level streaming call to a single provider."""
        override = self._resolve_task_override(task)
        provider_name = provider or self.primary_provider.value
        if override and override.get("provider"):
            provider_name = str(override["provider"])
        model = model or (override or {}).get("model")
        inst = self.get_provider(provider_name)
        if inst is None:
            raise ValueError(f"Provider '{provider_name}' is not available")
        if self._budget_exhausted(inst):
            raise RuntimeError(f"Daily LLM budget (${self.daily_budget_usd:.2f}) exhausted")
        async for chunk in inst.stream(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        ):
            yield chunk

    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        fallback_chain: list[Any] | None = None,
        task: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Generate text stream with fallback chain; yields degradation text on total failure."""
        messages: list[Message] = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        chain = self._resolve_chain(fallback_chain, task)
        for provider_name in chain:
            try:
                inst = self.get_provider(provider_name)
                if inst is None or self._budget_exhausted(inst):
                    continue
                async for chunk in self.stream(
                    messages,
                    provider=provider_name,
                    task=task,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM provider %s stream failed: %s", provider_name, exc)
        logger.error("All LLM providers failed stream for prompt %r", prompt[:60])
        yield DEGRADATION_TEXT

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        fallback_chain: list[Any] | None = None,
        task: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text with fallback chain; frozen-compat signature."""
        messages: list[Message] = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=prompt))
        chain = self._resolve_chain(fallback_chain, task)
        for provider_name in chain:
            try:
                response = await self.complete(
                    messages,
                    provider=provider_name,
                    task=task,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM provider %s failed: %s", provider_name, exc)
        logger.error("All LLM providers failed for prompt %r", prompt[:60])
        return DEGRADATION_TEXT

    async def health_check(self, provider_name: str | None = None) -> bool:
        """Configuration + light reachability probe for `jobot doctor`."""
        targets = [provider_name] if provider_name else [self.primary_provider.value]
        for name in targets:
            inst = self.get_provider(name)
            if inst is None:
                continue
            if await inst.health_check():
                return True
        return False

    def list_configured_providers(self) -> list[str]:
        return [name for name in PROVIDER_REGISTRY if self._api_key_for(name)]
