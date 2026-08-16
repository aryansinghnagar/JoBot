"""Concrete LLM provider implementations + registry (plan.md Chapter 6).

HTTP providers (OpenAI, Anthropic, OpenAI-compatible, Mistral, Cohere) use
stdlib urllib through `jobot.llm.base.http_post_json` so tests can
monkeypatch a single call site. Gemini/Vertex reuse the existing
`google-genai` dependency; Bedrock uses boto3 (optional `[providers]` extra,
lazy-imported and run off the event loop).
"""

import logging
import os
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Type, Union

from jobot.llm.base import (
    LLMProvider,
    LLMResponse,
    Message,
    ProviderPricing,
    ToolSpec,
    estimate_tokens,
    http_get_json,
    http_post_json,
)
from jobot.llm.pricing import PricingTable

logger = logging.getLogger(__name__)


class HTTPChatProvider(LLMProvider):
    """Shared behavior for REST chat-completion providers."""

    def __init__(self, pricing_table: Optional[PricingTable] = None) -> None:
        super().__init__(pricing_table or PricingTable())

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float:
        p = self._resolve_pricing(model)
        return round((input_tokens * p.input_per_1k + output_tokens * p.output_per_1k) / 1000.0, 6)

    def _api_key(self) -> Optional[str]:
        env_key = os.getenv(f"{self.name.upper()}_API_KEY")
        if env_key:
            return env_key
        if self.key_lookup is not None:
            return self.key_lookup()
        return None

    async def health_check(self) -> bool:
        return self._api_key() is not None


class OpenAIProvider(HTTPChatProvider):
    name = "openai"
    default_model = "gpt-4o-mini"
    api_url = "https://api.openai.com/v1/chat/completions"

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        m = self._resolve_model(model)
        payload = {
            "model": m,
            "messages": [msg.model_dump() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t.model_dump()} for t in tools]
        resp = http_post_json(
            self.api_url,
            {
                "Authorization": f"Bearer {self._api_key() or ''}",
                "Content-Type": "application/json",
            },
            payload,
            timeout_s,
        )
        text = str(resp["choices"][0]["message"]["content"] or "")
        usage = resp.get("usage") or {}
        in_tok = int(
            usage.get("prompt_tokens") or estimate_tokens(" ".join(msg.content for msg in messages))
        )
        out_tok = int(usage.get("completion_tokens") or estimate_tokens(text))
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("OpenAI streaming lands in a later phase")


class OpenAICompatProvider(OpenAIProvider):
    """Any OpenAI-compatible REST endpoint (OpenRouter/Groq/Together/Ollama/vLLM)."""

    def __init__(
        self,
        base_url: str,
        default_model: str = "default",
        pricing_table: Optional[PricingTable] = None,
    ) -> None:
        super().__init__(pricing_table or PricingTable())
        self.api_url = f"{base_url.rstrip('/')}/chat/completions"
        self.default_model = default_model
        self.name = "openai_compat"
        if default_model != "default":
            self.pricing[default_model] = ProviderPricing()

    def _api_key(self) -> Optional[str]:
        if self.key_lookup is not None:
            return self.key_lookup()
        return os.getenv("OPENAI_COMPAT_API_KEY")

    async def health_check(self) -> bool:
        if not self._api_key():
            return False
        base = self.api_url.rsplit("/chat/completions", 1)[0]
        headers = {"Authorization": f"Bearer {self._api_key() or ''}"}
        try:
            http_get_json(f"{base}/models", headers, timeout_s=5.0)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAICompat health probe failed: %s", exc)
            return False


class AnthropicProvider(HTTPChatProvider):
    name = "anthropic"
    default_model = "claude-3-5-haiku-20241022"
    api_url = "https://api.anthropic.com/v1/messages"

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        m = self._resolve_model(model)
        payload: Dict[str, Any] = {
            "model": m,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [msg.model_dump() for msg in messages if msg.role != "system"],
        }
        system = " ".join(msg.content for msg in messages if msg.role == "system")
        if system:
            payload["system"] = system
        resp = http_post_json(
            self.api_url,
            {
                "x-api-key": self._api_key() or "",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            payload,
            timeout_s,
        )
        text = str(resp["content"][0]["text"])
        usage = resp.get("usage") or {}
        in_tok = int(
            usage.get("input_tokens") or estimate_tokens(" ".join(msg.content for msg in messages))
        )
        out_tok = int(usage.get("output_tokens") or estimate_tokens(text))
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("Anthropic streaming lands in a later phase")


class MistralProvider(HTTPChatProvider):
    name = "mistral"
    default_model = "mistral-small-latest"
    api_url = "https://api.mistral.ai/v1/chat/completions"

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        m = self._resolve_model(model)
        payload = {
            "model": m,
            "messages": [msg.model_dump() for msg in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = http_post_json(
            self.api_url,
            {
                "Authorization": f"Bearer {self._api_key() or ''}",
                "Content-Type": "application/json",
            },
            payload,
            timeout_s,
        )
        text = str(resp["choices"][0]["message"]["content"] or "")
        usage = resp.get("usage") or {}
        in_tok = int(
            usage.get("prompt_tokens") or estimate_tokens(" ".join(msg.content for msg in messages))
        )
        out_tok = int(usage.get("completion_tokens") or estimate_tokens(text))
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("Mistral streaming lands in a later phase")


class CohereProvider(HTTPChatProvider):
    name = "cohere"
    default_model = "command-r"
    api_url = "https://api.cohere.com/v2/chat"

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        m = self._resolve_model(model)
        system = " ".join(msg.content for msg in messages if msg.role == "system")
        chat_messages = [msg.model_dump() for msg in messages if msg.role != "system"]
        payload: Dict[str, Any] = {
            "model": m,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system_prompt"] = system
        resp = http_post_json(
            self.api_url,
            {
                "Authorization": f"Bearer {self._api_key() or ''}",
                "Content-Type": "application/json",
            },
            payload,
            timeout_s,
        )
        text = str(resp["message"]["content"][0]["text"])
        in_tok = estimate_tokens(" ".join(msg.content for msg in messages))
        out_tok = estimate_tokens(text)
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("Cohere streaming lands in a later phase")


class GeminiProvider(LLMProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, pricing_table: Optional[PricingTable] = None) -> None:
        super().__init__(pricing_table or PricingTable())

    def _api_key(self) -> Optional[str]:
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            return env_key
        if self.key_lookup is not None:
            return self.key_lookup()
        return None

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float:
        p = self._resolve_pricing(model)
        return round((input_tokens * p.input_per_1k + output_tokens * p.output_per_1k) / 1000.0, 6)

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        from google import genai  # already a core dependency
        from google.genai import types

        m = self._resolve_model(model)
        client = genai.Client(api_key=self._api_key())
        system = " ".join(msg.content for msg in messages if msg.role == "system")
        prompt_text = " ".join(msg.content for msg in messages if msg.role != "system")
        config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens)
        if system:
            config.system_instruction = system
        response = await client.aio.models.generate_content(
            model=m, contents=prompt_text, config=config
        )
        text = (response.text or "").strip()
        meta = (response.usage_metadata or None) if hasattr(response, "usage_metadata") else None
        in_tok = int(
            getattr(meta, "prompt_token_count", 0)
            or estimate_tokens(" ".join(msg.content for msg in messages))
        )
        out_tok = int(getattr(meta, "candidates_token_count", 0) or estimate_tokens(text))
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("Gemini streaming lands in a later phase")

    async def health_check(self) -> bool:
        return self._api_key() is not None


class VertexProvider(GeminiProvider):
    """Google Vertex AI via the google-genai vertexai client (ADC credentials)."""

    name = "vertex"

    def _api_key(self) -> Optional[str]:
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            return env_key
        if self.key_lookup is not None:
            return self.key_lookup()
        return "vertex-adc"

    def _project_location(self) -> Any:
        return (os.getenv("GOOGLE_CLOUD_PROJECT", ""), os.getenv("VERTEX_LOCATION", "us-central1"))

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        from google import genai  # already a core dependency
        from google.genai import types

        m = self._resolve_model(model)
        project, location = self._project_location()
        client = genai.Client(vertexai=True, project=project, location=location)
        system = " ".join(msg.content for msg in messages if msg.role == "system")
        prompt_text = " ".join(msg.content for msg in messages if msg.role != "system")
        config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens)
        if system:
            config.system_instruction = system
        response = await client.aio.models.generate_content(
            model=m, contents=prompt_text, config=config
        )
        text = (response.text or "").strip()
        in_tok = estimate_tokens(" ".join(msg.content for msg in messages))
        out_tok = estimate_tokens(text)
        return LLMResponse(
            provider=self.name,
            model=m,
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            estimated_cost_usd=self.estimate_cost(in_tok, out_tok, m),
        )

    async def health_check(self) -> bool:
        return bool(os.getenv("GOOGLE_CLOUD_PROJECT"))


class BedrockProvider(LLMProvider):
    """AWS Bedrock via boto3 (optional `[providers]` extra, lazy import)."""

    name = "bedrock"
    default_model = "anthropic.claude-3-5-haiku-20241022-v1:0"

    def __init__(self, pricing_table: Optional[PricingTable] = None) -> None:
        super().__init__(pricing_table or PricingTable())

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float:
        p = self._resolve_pricing(model)
        return round((input_tokens * p.input_per_1k + output_tokens * p.output_per_1k) / 1000.0, 6)

    def _region(self) -> str:
        return os.getenv("AWS_REGION", "us-east-1")

    def _converse(
        self,
        messages: List[Message],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        import boto3  # optional extra; lazy import keeps core install light

        client = boto3.client("bedrock-runtime", region_name=self._region())
        system = [{"text": msg.content} for msg in messages if msg.role == "system"]
        body = [
            {"role": msg.role, "content": [{"text": msg.content}]}
            for msg in messages
            if msg.role != "system"
        ]
        resp = client.converse(
            modelId=model,
            messages=body,
            system=system,
            inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
        )
        text = "".join(
            str(part.get("text", ""))
            for part in resp["output"]["message"]["content"]
            if "text" in part
        )
        usage = resp.get("usage") or {}
        return {
            "text": text,
            "input_tokens": int(
                usage.get("inputTokens")
                or estimate_tokens(" ".join(msg.content for msg in messages))
            ),
            "output_tokens": int(usage.get("outputTokens") or estimate_tokens(text)),
        }

    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[ToolSpec]] = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        m = self._resolve_model(model)
        start = __import__("time").monotonic()
        result = await self._run_in_thread(self._converse, messages, m, temperature, max_tokens)
        return LLMResponse(
            provider=self.name,
            model=m,
            text=result["text"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            estimated_cost_usd=self.estimate_cost(
                result["input_tokens"], result["output_tokens"], m
            ),
            latency_ms=self._timed(start),
        )

    async def stream(self, messages: List[Message], **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError("Bedrock streaming lands in a later phase")

    async def health_check(self) -> bool:
        try:
            import boto3  # noqa: F401

            return True
        except ImportError:
            return False


def _openrouter() -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url="https://openrouter.ai/api/v1", default_model="default")


def _groq() -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url="https://api.groq.com/openai/v1", default_model="default")


def _together() -> OpenAICompatProvider:
    return OpenAICompatProvider(base_url="https://api.together.xyz/v1", default_model="default")


def _ollama() -> OpenAICompatProvider:
    return OpenAICompatProvider(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        default_model=os.getenv("OLLAMA_MODEL", "llama3"),
    )


def _vllm() -> OpenAICompatProvider:
    base = os.getenv("VLLM_BASE_URL", "")
    if not base:
        raise ValueError("VLLM_BASE_URL must be set to instantiate the vllm provider")
    return OpenAICompatProvider(base_url=base, default_model="default")


# plan.md Chapter 6 PROVIDER_REGISTRY: six classes, twelve concrete instances.
ProviderFactory = Union[Type[LLMProvider], Callable[[], LLMProvider]]
PROVIDER_REGISTRY: Dict[str, ProviderFactory] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openrouter": _openrouter,
    "groq": _groq,
    "together": _together,
    "ollama": _ollama,
    "vllm": _vllm,
    "mistral": MistralProvider,
    "cohere": CohereProvider,
    "bedrock": BedrockProvider,
    "vertex": VertexProvider,
}
