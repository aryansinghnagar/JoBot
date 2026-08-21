"""Tests for ModelRouter and SemanticCache integration (Phase 3 / WS-AI)."""

from unittest.mock import AsyncMock, patch

import pytest

from jobot.llm.base import LLMResponse, Message
from jobot.llm.router import ModelProvider, ModelRouter
from jobot.llm.semantic_cache import SemanticCache


@pytest.mark.asyncio
async def test_model_router_cache_hit():
    cache = SemanticCache()
    router = ModelRouter(primary_provider=ModelProvider.OPENAI, cache=cache)

    mock_resp = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        text="Fast cached answer",
        input_tokens=12,
        output_tokens=24,
        estimated_cost_usd=0.001,
    )

    with patch.object(router, "_instantiate_provider") as mock_inst:
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_resp
        mock_provider.health_check.return_value = True
        mock_inst.return_value = mock_provider

        messages = [Message(role="user", content="Explain Python async")]

        # First call: cache miss, provider invoked
        res1 = await router.complete(messages, provider="openai", model="gpt-4o-mini")
        assert res1.text == "Fast cached answer"
        assert mock_provider.complete.call_count == 1
        assert cache.misses == 1

        # Second call: cache hit, provider NOT invoked again
        res2 = await router.complete(messages, provider="openai", model="gpt-4o-mini")
        assert res2.text == "Fast cached answer"
        assert mock_provider.complete.call_count == 1  # Still 1
        assert cache.hits == 1


@pytest.mark.asyncio
async def test_model_router_cache_bypass():
    cache = SemanticCache()
    router = ModelRouter(primary_provider=ModelProvider.OPENAI, cache=cache)

    mock_resp = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        text="Fresh answer",
        input_tokens=10,
        output_tokens=20,
    )

    with patch.object(router, "_instantiate_provider") as mock_inst:
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_resp
        mock_inst.return_value = mock_provider

        messages = [Message(role="user", content="Random nonce 12345")]

        # Call with use_cache=False
        res = await router.complete(
            messages, provider="openai", model="gpt-4o-mini", use_cache=False
        )
        assert res.text == "Fresh answer"
        assert cache.hits == 0
        assert cache.misses == 0
