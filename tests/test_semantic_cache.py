"""Unit tests for SemanticCache (Phase 3 LLM-Ops)."""

import time

from jobot.llm.base import LLMResponse
from jobot.llm.semantic_cache import SemanticCache


def test_semantic_cache_in_memory():
    cache = SemanticCache(default_ttl=10.0)
    messages = [{"role": "user", "content": "What is Python?"}]
    model = "gpt-4o-mini"

    assert cache.get(messages, model) is None
    assert cache.misses == 1

    resp = LLMResponse(
        provider="openai",
        model="gpt-4o-mini",
        text="Python is a programming language.",
        input_tokens=10,
        output_tokens=20,
    )
    cache.set(messages, model, resp)

    cached = cache.get(messages, model)
    assert cached is not None
    assert cached.text == "Python is a programming language."
    assert cache.hits == 1
    assert cached.estimated_cost_usd == 0.0


def test_semantic_cache_sqlite_persistence(tmp_path):
    db_file = tmp_path / "cache.db"
    cache1 = SemanticCache(db_path=db_file, default_ttl=5.0)
    messages = [{"role": "user", "content": "Describe AWS EC2."}]
    model = "gemini-1.5-flash"

    resp = LLMResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        text="AWS EC2 is a cloud compute service.",
        input_tokens=15,
        output_tokens=30,
    )
    cache1.set(messages, model, resp)

    # Instantiate a second cache instance reading from the same sqlite db
    cache2 = SemanticCache(db_path=db_file, default_ttl=5.0)
    cached = cache2.get(messages, model)
    assert cached is not None
    assert cached.text == "AWS EC2 is a cloud compute service."
    assert cache2.hits == 1


def test_semantic_cache_expiry():
    cache = SemanticCache(default_ttl=0.01)
    messages = [{"role": "user", "content": "Temporary message"}]
    model = "claude-3-5-haiku"

    resp = LLMResponse(
        provider="anthropic",
        model="claude-3-5-haiku",
        text="Will expire soon.",
    )
    cache.set(messages, model, resp, ttl_seconds=0.05)
    time.sleep(0.1)
    assert cache.get(messages, model) is None
