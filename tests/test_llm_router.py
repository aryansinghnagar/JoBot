"""ModelRouter v2 tests: routing, fallback, budget cap, persistence, keyring."""

import json
from typing import Any, Dict, List, Optional

import pytest

from jobot.llm.base import LLMResponse, Message
from jobot.llm.router import DEFAULT_FALLBACK_CHAIN, DEGRADATION_TEXT, ModelRouter
from jobot.secrets import set_secret


class FakeKeyring:
    def __init__(self) -> None:
        self._store: dict[tuple, str] = {}

    def get_password(self, service: str, key: str) -> str | None:
        return self._store.get((service, key))

    def set_password(self, service: str, key: str, value: str) -> None:
        self._store[(service, key)] = value

    def delete_password(self, service: str, key: str) -> None:
        self._store.pop((service, key), None)


@pytest.fixture
def fake_keyring(monkeypatch):
    import keyring

    backend = FakeKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    return backend


@pytest.fixture
def clean_env(monkeypatch):
    for key in (
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "COHERE_API_KEY",
        "OLLAMA_MODEL",
        "GOOGLE_CLOUD_PROJECT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("JOBOT_DEFAULT_LLM_PROVIDER", raising=False)
    monkeypatch.setattr(ModelRouter, "_load_dotenv", lambda self: None)
    return monkeypatch


def _router(monkeypatch, tmp_path, **kwargs: Any) -> ModelRouter:
    monkeypatch.setenv("HOME", str(tmp_path))
    return ModelRouter(spend_path=tmp_path / "llm_spend.json", **kwargs)


class StubProvider:
    """Minimal fake LLMProvider: exercises the router's real budget/routing logic."""

    def __init__(self, name: str, fail: bool = False) -> None:
        self.name = name
        self.fail = fail

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[Any] | None = None,
        timeout_s: float = 60.0,
    ) -> LLMResponse:
        if self.fail:
            raise RuntimeError(f"{self.name} down")
        return LLMResponse(
            provider=self.name,
            model=model or self.name,
            text=f"chain ok via {self.name}",
            input_tokens=10,
            output_tokens=4,
            estimated_cost_usd=0.001,
        )


def _install_stub_providers(monkeypatch, failing: list[str]) -> None:
    def factory(self: ModelRouter, name: str):
        return StubProvider(name, fail=name in failing)

    monkeypatch.setattr(ModelRouter, "get_provider", factory)


@pytest.mark.asyncio
async def test_generate_text_fallback_chain(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)
    _install_stub_providers(monkeypatch, failing=["gemini"])
    text = await router.generate_text("hello", fallback_chain=["gemini", "openai"])
    assert text == "chain ok via openai"


@pytest.mark.asyncio
async def test_generate_text_all_fail_degrades(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)
    _install_stub_providers(monkeypatch, failing=["gemini", "openai", "anthropic", "ollama"])
    text = await router.generate_text(
        "hello", fallback_chain=["gemini", "openai", "anthropic", "ollama"]
    )
    assert text == DEGRADATION_TEXT


@pytest.mark.asyncio
async def test_budget_exhausted_falls_back_to_local(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path, daily_budget_usd=0.001)
    router._record_spend(0.002)
    _install_stub_providers(monkeypatch, failing=[])
    text = await router.generate_text("hello", fallback_chain=["gemini", "ollama"])
    assert text == "chain ok via ollama"
    assert router.metrics_history[-1].provider == "ollama"


@pytest.mark.asyncio
async def test_spend_persisted_across_instances(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)
    _install_stub_providers(monkeypatch, failing=[])
    await router.generate_text("hello", fallback_chain=["gemini"])
    assert router.current_spent_usd > 0
    reloaded = _router(monkeypatch, tmp_path)
    assert reloaded.current_spent_usd == pytest.approx(router.current_spent_usd)
    spend_file = json.loads((tmp_path / "llm_spend.json").read_text(encoding="utf-8"))
    assert spend_file[router.today_key] == pytest.approx(router.current_spent_usd)


def test_keyring_api_key_lookup(clean_env, fake_keyring):
    set_secret("llm.api_key.openai", "sk-keyring-test")
    router = ModelRouter()
    provider = router.get_provider("openai")
    assert provider is not None
    assert provider._api_key() == "sk-keyring-test"
    assert "openai" in router.list_configured_providers()


def test_env_key_precedes_keyring(clean_env, fake_keyring, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test")
    set_secret("llm.api_key.openai", "sk-keyring-test")
    router = ModelRouter()
    provider = router.get_provider("openai")
    assert provider is not None
    assert provider._api_key() == "sk-env-test"


def test_default_fallback_chain_matches_legacy():
    router = ModelRouter()
    chain = router._resolve_chain(None, None)
    assert chain == DEFAULT_FALLBACK_CHAIN


def test_task_override_resolves_provider(monkeypatch, tmp_path):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "default.yaml").write_text(
        "llm:\n  task_overrides:\n    resume_tailoring:\n      provider: anthropic\n      model: claude-3-5-sonnet-20241022\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("jobot.config.profile.DEFAULT_PROFILE_DIR", profile_dir)
    router = ModelRouter()
    chain = router._resolve_chain(None, "resume_tailoring")
    assert chain[0] == "anthropic"
    override = router._resolve_task_override("resume_tailoring")
    assert override["model"] == "claude-3-5-sonnet-20241022"


def test_unknown_provider_reports_none(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)
    assert router.get_provider("nonexistent") is None


@pytest.mark.asyncio
async def test_health_check_configured_provider(clean_env, fake_keyring, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "ai-test-key")
    router = ModelRouter()
    assert await router.health_check("gemini") is True
    assert await router.health_check("openai") is False


class StubStreamProvider(StubProvider):
    async def stream(self, messages: list[Message], **kwargs: Any):
        if self.fail:
            raise RuntimeError(f"{self.name} stream down")
        for chunk in [f"{self.name} ", "chunk"]:
            yield chunk


@pytest.mark.asyncio
async def test_router_generate_text_stream_fallback(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)

    def factory(self: ModelRouter, name: str):
        return StubStreamProvider(name, fail=(name == "gemini"))

    monkeypatch.setattr(ModelRouter, "get_provider", factory)
    chunks = [
        chunk
        async for chunk in router.generate_text_stream(
            "test prompt", fallback_chain=["gemini", "openai"]
        )
    ]
    assert "".join(chunks) == "openai chunk"


@pytest.mark.asyncio
async def test_router_generate_text_stream_all_fail_yields_degradation(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)

    def factory(self: ModelRouter, name: str):
        return StubStreamProvider(name, fail=True)

    monkeypatch.setattr(ModelRouter, "get_provider", factory)
    chunks = [
        chunk
        async for chunk in router.generate_text_stream(
            "test prompt", fallback_chain=["gemini", "openai"]
        )
    ]
    assert "".join(chunks) == DEGRADATION_TEXT


# ---------------------------------------------------------------------------
# Phase B3 (JOB-ARC-002): KeyboardInterrupt must propagate through
# ``generate_text``. The fallback-chain ``except`` block was previously a bare
# ``except Exception``, which would have swallowed any ``Exception`` subclass
# — including ``KeyboardInterrupt`` if it had been a subclass of ``Exception``
# (it is not; it derives from ``BaseException``). This test asserts the
# contract is preserved: a provider raising ``KeyboardInterrupt`` aborts the
# fallback chain instead of returning the degradation text.
# ---------------------------------------------------------------------------


class _KeyboardInterruptProvider(StubProvider):
    async def complete(self, *args: Any, **kwargs: Any) -> LLMResponse:
        raise KeyboardInterrupt("user pressed Ctrl+C")


@pytest.mark.asyncio
async def test_generate_text_propagates_keyboard_interrupt(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)

    def factory(self: ModelRouter, name: str):
        return _KeyboardInterruptProvider(name)

    monkeypatch.setattr(ModelRouter, "get_provider", factory)
    with pytest.raises(KeyboardInterrupt):
        await router.generate_text("hello", fallback_chain=["gemini", "openai"])


@pytest.mark.asyncio
async def test_generate_text_stream_propagates_keyboard_interrupt(monkeypatch, tmp_path):
    router = _router(monkeypatch, tmp_path)

    class _StreamKbdProvider(StubProvider):
        async def stream(self, *args: Any, **kwargs: Any):
            raise KeyboardInterrupt("user pressed Ctrl+C")
            yield ""  # pragma: no cover — unreachable, makes this an async gen

    def factory(self: ModelRouter, name: str):
        return _StreamKbdProvider(name)

    monkeypatch.setattr(ModelRouter, "get_provider", factory)
    with pytest.raises(KeyboardInterrupt):
        async for _ in router.generate_text_stream("hello", fallback_chain=["gemini", "openai"]):
            pass
