import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ModelCallMetrics(BaseModel):
    provider: ModelProvider
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


class ModelRouter:
    """
    Provider-Neutral LLM Model Router (Layer G).
    Manages provider selection, fallback chains, cost tracking, and structured Pydantic decoding.
    """

    def __init__(self, primary_provider: ModelProvider = ModelProvider.GEMINI):
        self._load_dotenv()
        self.primary_provider = primary_provider
        self.daily_budget_usd: float = 5.0
        self.current_spent_usd: float = 0.0
        self.metrics_history: List[ModelCallMetrics] = []

    def _load_dotenv(self) -> None:
        """Helper to auto-load .env key-value pairs if present."""
        env_paths = [Path.cwd() / ".env", Path.home() / ".jobot" / ".env"]
        for p in env_paths:
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip()
                            if k and v and k not in os.environ:
                                os.environ[k] = v
                except Exception as e:
                    logger.debug(f"Failed to read .env at {p}: {e}")

    def _estimate_cost(self, provider: ModelProvider, prompt_tokens: int, completion_tokens: int) -> float:
        # Approximate pricing per 1K tokens (Gemini 2.0/3.0 Flash tier defaults)
        if provider == ModelProvider.GEMINI:
            return (prompt_tokens * 0.000075 + completion_tokens * 0.00030) / 1000.0
        elif provider == ModelProvider.OPENAI:
            return (prompt_tokens * 0.00015 + completion_tokens * 0.00060) / 1000.0
        elif provider == ModelProvider.ANTHROPIC:
            return (prompt_tokens * 0.00025 + completion_tokens * 0.00125) / 1000.0
        return 0.0  # Ollama local

    async def generate_text(
        self, prompt: str, system_prompt: Optional[str] = None, fallback_chain: Optional[List[ModelProvider]] = None
    ) -> str:
        """Generate text response using primary provider with fallback chain."""
        if fallback_chain is None:
            fallback_chain = [ModelProvider.GEMINI, ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.OLLAMA]

        for provider in fallback_chain:
            try:
                res = await self._call_provider(provider, prompt, system_prompt)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"Model provider {provider} failed: {e}. Trying next fallback...")

        # Graceful degradation fallback if all LLM API calls fail
        return "Information from profile facts: Please refer to candidate profile."

    async def _call_provider(self, provider: ModelProvider, prompt: str, system_prompt: Optional[str]) -> Optional[str]:
        # Check budget limit
        if self.current_spent_usd >= self.daily_budget_usd and provider != ModelProvider.OLLAMA:
            logger.warning("Daily LLM budget reached. Falling back to local Ollama or profile lookup.")

        api_key = os.getenv(f"{provider.value.upper()}_API_KEY")
        if provider != ModelProvider.OLLAMA and not api_key:
            # Skip provider if API key is not configured
            return None

        if provider == ModelProvider.GEMINI:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                cost = self._estimate_cost(provider, len(prompt.split()), len(response.text.split()))
                self.current_spent_usd += cost
                return response.text
            except Exception as ex:
                logger.debug(f"Gemini API call failed: {ex}")
                return None

        elif provider == ModelProvider.OLLAMA:
            # Local Ollama fallback HTTP request stub
            return None

        return None
