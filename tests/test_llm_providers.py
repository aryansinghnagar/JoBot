"""Provider unit tests: mock HTTP / stub SDKs — no real network calls."""

import sys
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

from jobot.llm.base import LLMResponse, Message, ProviderPricing, ToolSpec
from jobot.llm.pricing import PricingTable
from jobot.llm.providers import (
    AnthropicProvider,
    BedrockProvider,
    CohereProvider,
    GeminiProvider,
    MistralProvider,
    OpenAICompatProvider,
    OpenAIProvider,
    VertexProvider,
)


@pytest.fixture
def mock_post(monkeypatch):
    calls: List[Dict[str, Any]] = []

    def fake_post(url, headers, payload, timeout_s=60.0):
        calls.append({"url": url, "headers": headers, "payload": payload})
        return _response_for(url)

    monkeypatch.setattr("jobot.llm.providers.http_post_json", fake_post)
    return calls


def _response_for(url: str) -> Dict[str, Any]:
    if "anthropic" in url:
        return {
            "content": [{"type": "text", "text": "anthropic reply"}],
            "usage": {"input_tokens": 12, "output_tokens": 5},
        }
    if "cohere" in url:
        return {"message": {"content": [{"type": "text", "text": "cohere reply"}]}}
    if "mistral" in url:
        return {
            "choices": [{"message": {"content": "mistral reply"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        }
    return {
        "choices": [{"message": {"content": "openai reply"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }


def _messages() -> List[Message]:
    return [Message(role="system", content="You are helpful."), Message(role="user", content="Hi")]


@pytest.mark.asyncio
async def test_openai_provider_complete(mock_post):
    provider = OpenAIProvider()
    resp = await provider.complete(_messages())
    assert isinstance(resp, LLMResponse)
    assert resp.text == "openai reply"
    assert resp.input_tokens == 10 and resp.output_tokens == 4
    assert resp.estimated_cost_usd > 0
    assert mock_post[0]["payload"]["model"] == "gpt-4o-mini"
    assert mock_post[0]["headers"]["Authorization"].startswith("Bearer ")


@pytest.mark.asyncio
async def test_anthropic_provider_complete(mock_post):
    provider = AnthropicProvider()
    resp = await provider.complete(_messages())
    assert resp.text == "anthropic reply"
    assert "system" in mock_post[0]["payload"]
    body = mock_post[0]["payload"]["messages"]
    assert all(m["role"] != "system" for m in body)


@pytest.mark.asyncio
async def test_mistral_provider_complete(mock_post):
    provider = MistralProvider()
    resp = await provider.complete(_messages(), model="mistral-large-latest")
    assert resp.text == "mistral reply"
    assert mock_post[0]["url"] == "https://api.mistral.ai/v1/chat/completions"


@pytest.mark.asyncio
async def test_cohere_provider_complete(mock_post):
    provider = CohereProvider()
    resp = await provider.complete(_messages())
    assert resp.text == "cohere reply"
    assert mock_post[0]["payload"]["system_prompt"] == "You are helpful."


@pytest.mark.asyncio
async def test_openai_compat_provider_base_url(monkeypatch):
    calls: List[Dict[str, Any]] = []

    def fake_post(url, headers, payload, timeout_s=60.0):
        calls.append(url)
        return {"choices": [{"message": {"content": "compat reply"}}], "usage": None}

    monkeypatch.setattr("jobot.llm.providers.http_post_json", fake_post)
    provider = OpenAICompatProvider(base_url="https://openrouter.ai/api/v1")
    resp = await provider.complete(_messages())
    assert resp.text == "compat reply"
    assert calls[0] == "https://openrouter.ai/api/v1/chat/completions"


@pytest.mark.asyncio
async def test_openai_compat_health_check_reachable(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-or-test")
    monkeypatch.setattr(
        "jobot.llm.providers.http_get_json",
        lambda url, headers=None, timeout_s=5.0: {"data": []},
    )
    provider = OpenAICompatProvider(base_url="https://openrouter.ai/api/v1")
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_openai_compat_health_check_unreachable(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "sk-or-test")

    def fail_get(url, headers=None, timeout_s=5.0):
        raise OSError("refused")

    monkeypatch.setattr("jobot.llm.providers.http_get_json", fail_get)
    provider = OpenAICompatProvider(base_url="https://openrouter.ai/api/v1")
    assert await provider.health_check() is False


class _FakeGenaiResponse:
    text = "gemini reply"
    usage_metadata = None


class _FakeGenaiModels:
    async def generate_content(self, *args: Any, **kwargs: Any) -> _FakeGenaiResponse:
        return _FakeGenaiResponse()


class _FakeGenaiAsync:
    models = _FakeGenaiModels()


class _FakeGenaiClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.aio = _FakeGenaiAsync()


def _install_fake_genai(monkeypatch) -> None:
    fake_types = SimpleNamespace(
        Content=lambda **kw: kw,
        Part=lambda **kw: kw,
        GenerateContentConfig=lambda **kw: SimpleNamespace(**kw),
    )
    fake_genai = SimpleNamespace(Client=_FakeGenaiClient, types=fake_types)
    monkeypatch.setitem(sys.modules, "google", SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


@pytest.mark.asyncio
async def test_gemini_provider_complete(monkeypatch):
    _install_fake_genai(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "ai-test")
    provider = GeminiProvider()
    resp = await provider.complete(_messages())
    assert resp.text == "gemini reply"
    assert resp.provider == "gemini"
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_vertex_provider_complete(monkeypatch):
    _install_fake_genai(monkeypatch)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-proj")
    provider = VertexProvider()
    resp = await provider.complete(_messages())
    assert resp.text == "gemini reply"
    assert resp.provider == "vertex"
    assert await provider.health_check() is True


class _FakeBedrockClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def converse(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "output": {"message": {"content": [{"text": "bedrock reply"}]}},
            "usage": {"inputTokens": 20, "outputTokens": 6},
        }


class _FakeBoto3:
    def client(self, *args: Any, **kwargs: Any) -> _FakeBedrockClient:
        return _FakeBedrockClient()


@pytest.mark.asyncio
async def test_bedrock_provider_complete(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", _FakeBoto3())
    provider = BedrockProvider()
    resp = await provider.complete(_messages())
    assert resp.text == "bedrock reply"
    assert resp.input_tokens == 20 and resp.output_tokens == 6
    assert resp.estimated_cost_usd > 0


@pytest.mark.asyncio
async def test_bedrock_provider_health_without_boto3(monkeypatch):
    monkeypatch.delitem(sys.modules, "boto3", raising=False)
    provider = BedrockProvider()
    assert await provider.health_check() is False


def test_estimate_cost_uses_pricing_table():
    provider = OpenAIProvider()
    # gpt-4o-mini: $0.15/1M in, $0.60/1M out -> 1000 in + 500 out = $0.00015 + $0.00030
    assert provider.estimate_cost(1000, 500) == pytest.approx(0.00045, rel=1e-3)


def test_pricing_table_loads_shipped_and_override(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    override = tmp_path / ".jobot" / "pricing.yaml"
    override.parent.mkdir(parents=True)
    override.write_text("openai:\n  my-custom-model:\n    input_per_1k: 0.001\n    output_per_1k: 0.002\n", encoding="utf-8")
    table = PricingTable()
    assert table.get("gemini", "gemini-2.5-flash").input_per_1k > 0
    assert table.get("openai", "my-custom-model") == ProviderPricing(
        input_per_1k=0.001, output_per_1k=0.002
    )
    assert table.get("unknown", "model") == ProviderPricing()


@pytest.mark.asyncio
async def test_openai_provider_optional_tools(mock_post):
    provider = OpenAIProvider()
    resp = await provider.complete(_messages(), tools=[ToolSpec(name="lookup", description="d")])
    assert resp.text == "openai reply"
    assert mock_post[0]["payload"]["tools"][0]["function"]["name"] == "lookup"