"""Live-API provider integration tests — opt-in.

These hit real (paid) LLM APIs, so the default `pytest` run skips them:
    $env:JOBOT_RUN_LIVE_LLM=1; pytest tests/integration/test_llm_providers_live.py
Only providers with a configured key (env or `jobot config set`) run.
"""

import os

import pytest

from jobot.llm.base import Message
from jobot.llm.router import ModelRouter

pytestmark = pytest.mark.skipif(
    os.getenv("JOBOT_RUN_LIVE_LLM") != "1",
    reason="live LLM tests opt-in via JOBOT_RUN_LIVE_LLM=1",
)

MESSAGES = [
    Message(role="user", content="Reply with exactly the word: ready"),
]


def _configured_providers() -> list[str]:
    return [name for name in ("gemini", "openai", "anthropic", "mistral", "cohere", "openrouter") if os.getenv(f"{name.upper()}_API_KEY")]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("provider", _configured_providers())
async def test_live_provider_call(provider: str) -> None:
    router = ModelRouter()
    response = await router.complete(MESSAGES, provider=provider, max_tokens=16)
    assert response.text
    assert response.provider == provider
    assert response.estimated_cost_usd >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_router_generate_text() -> None:
    if not _configured_providers():
        pytest.skip("no provider API key configured")
    router = ModelRouter()
    text = await router.generate_text("Reply with exactly one word: ready", max_tokens=16)
    assert text and "LLM_UNAVAILABLE" not in text