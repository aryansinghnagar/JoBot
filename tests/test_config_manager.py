"""Config manager + profiles YAML tests (FakeKeyring; no real keyring writes)."""

from typing import Dict, Optional

import pytest

from jobot.config.manager import ConfigManager
from jobot.config.profile import (
    ProfileConfig,
    load_llm_settings,
    load_profile_config,
    profile_config_path,
)
from jobot.secrets import get_secret


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
def manager(tmp_path, fake_keyring, monkeypatch):
    monkeypatch.delenv("JOBOT_LLM_DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("JOBOT_DEFAULT_LLM_PROVIDER", raising=False)
    return ConfigManager(config_path=tmp_path / "config.yaml")


def test_secret_key_roundtrip_via_keyring(manager):
    manager.set("llm.api_key.gemini", "AIza-secret")
    assert get_secret("llm.api_key.gemini") == "AIza-secret"
    assert manager.get("llm.api_key.gemini") == "AIza-secret"
    manager.unset("llm.api_key.gemini")
    assert manager.get("llm.api_key.gemini") is None


def test_nonsecret_key_roundtrip_via_file(manager):
    manager.set("llm.default_provider", "anthropic")
    manager.set("llm.daily_cost_cap_usd", "2.5")
    reloaded = ConfigManager(config_path=manager.config_path)
    assert reloaded.get("llm.default_provider") == "anthropic"
    assert reloaded.get("llm.daily_cost_cap_usd") == "2.5"
    assert manager.get("llm.default_provider") == "anthropic"


def test_env_override_beats_file(manager, monkeypatch):
    manager.set("llm.default_provider", "anthropic")
    monkeypatch.setenv("JOBOT_LLM_DEFAULT_PROVIDER", "cohere")
    assert manager.get("llm.default_provider") == "cohere"


def test_legacy_env_alias(manager, monkeypatch):
    monkeypatch.setenv("JOBOT_DEFAULT_LLM_PROVIDER", "mistral")
    assert manager.get("llm.default_provider") == "mistral"


def test_unset_nonsecret(manager):
    manager.set("llm.default_provider", "gemini")
    manager.unset("llm.default_provider")
    assert manager.get("llm.default_provider") is None


def test_show_masked_hides_secrets(manager):
    manager.set("llm.default_provider", "gemini")
    manager.set("llm.api_key.gemini", "AIzaSy0123456789abcdef")
    shown = manager.show_masked()
    assert shown["llm.default_provider"] == "gemini"
    assert "AIzaSy0123456789abcdef" not in " ".join(shown.values())
    assert shown["llm.api_key.gemini"].endswith("***")


def test_missing_config_file_defaults(manager):
    assert manager.get("llm.default_provider") is None
    assert manager.get("llm.daily_cost_cap_usd", "5.0") == "5.0"


def test_profile_loader_parses_yaml(tmp_path, monkeypatch):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "default.yaml").write_text(
        "search:\n"
        "  keywords: [python, kubernetes]\n"
        "  location: San Francisco\n"
        "  sites: [linkedin, greenhouse]\n"
        "target:\n"
        "  min_salary_usd: 180000\n"
        "  blacklisted_companies: [Acme]\n"
        "resume_base:\n"
        "  summary: Senior backend engineer\n"
        "  skills: [Python, Go]\n"
        "  experience:\n"
        "    - company: Stripe\n"
        "      title: Senior Engineer\n"
        "      dates: 2022-2026\n"
        "llm:\n"
        "  default_provider: anthropic\n"
        "  fallback_chain: [anthropic, gemini]\n"
        "  daily_cost_cap_usd: 3.5\n"
        "  task_overrides:\n"
        "    resume_tailoring:\n"
        "      provider: anthropic\n"
        "      model: claude-3-5-sonnet-20241022\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("jobot.config.profile.DEFAULT_PROFILE_DIR", profile_dir)
    config = load_profile_config()
    assert isinstance(config, ProfileConfig)
    assert config.search.keywords == ["python", "kubernetes"]
    assert config.target.min_salary_usd == 180000
    assert config.resume_base.experience[0].company == "Stripe"
    llm = load_llm_settings()
    assert llm.default_provider == "anthropic"
    assert llm.daily_cost_cap_usd == 3.5
    assert llm.task_overrides["resume_tailoring"].provider == "anthropic"


def test_profile_loader_missing_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("jobot.config.profile.DEFAULT_PROFILE_DIR", tmp_path)
    config = load_profile_config()
    assert config.search.keywords == []
    assert load_llm_settings().default_provider == "gemini"


def test_profile_env_selection(tmp_path, monkeypatch):
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    (profile_dir / "work.yaml").write_text("search:\n  location: London\n", encoding="utf-8")
    monkeypatch.setattr("jobot.config.profile.DEFAULT_PROFILE_DIR", profile_dir)
    monkeypatch.setenv("JOBOT_PROFILE", "work")
    assert profile_config_path().name == "work.yaml"
    assert load_profile_config().search.location == "London"


def test_llm_env_override_default_provider(tmp_path, monkeypatch):
    monkeypatch.setattr("jobot.config.profile.DEFAULT_PROFILE_DIR", tmp_path)
    monkeypatch.setenv("JOBOT_DEFAULT_LLM_PROVIDER", "ollama")
    assert load_llm_settings().default_provider == "ollama"
