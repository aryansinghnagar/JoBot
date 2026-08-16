"""`jobot doctor` + `jobot config` CLI end-to-end tests (FakeKeyring)."""

from typing import Dict, Optional

import pytest
from typer.testing import CliRunner

from jobot.cli.main import app

runner = CliRunner()


class FakeKeyring:
    def __init__(self) -> None:
        self._store: Dict[tuple, str] = {}

    def get_password(self, service: str, key: str) -> Optional[str]:
        return self._store.get((service, key))

    def set_password(self, service: str, key: str, value: str) -> None:
        self._store[(service, key)] = value

    def delete_password(self, service: str, key: str) -> None:
        self._store.pop((service, key), None)


@pytest.fixture
def fake_keyring(monkeypatch):
    import keyring

    from jobot.llm.router import ModelRouter

    backend = FakeKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    for key in (
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "COHERE_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("JOBOT_DEFAULT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.setattr(ModelRouter, "_load_dotenv", lambda self: None)
    return backend


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".jobot" / "profiles").mkdir(parents=True)
    return tmp_path


def test_config_set_get_roundtrip(fake_keyring, isolated_home):
    result = runner.invoke(app, ["config", "set", "llm.default_provider", "anthropic"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "get", "llm.default_provider"])
    assert result.exit_code == 0
    assert "anthropic" in result.output


def test_config_set_secret_to_keyring(fake_keyring, isolated_home):
    result = runner.invoke(app, ["config", "set", "llm.api_key.gemini", "AIzaSyTEST"])
    assert result.exit_code == 0
    assert "OS keyring" in result.output
    result = runner.invoke(app, ["config", "get", "llm.api_key.gemini"])
    assert "AIzaSyTEST" in result.output


def test_config_show_masks_secrets(fake_keyring, isolated_home):
    runner.invoke(app, ["config", "set", "llm.api_key.gemini", "AIzaSyVERYSECRETVALUE"])
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "AIzaSyVERYSECRETVALUE" not in result.output
    assert "AIza***" in result.output


def test_config_get_missing_key_errors(fake_keyring, isolated_home):
    result = runner.invoke(app, ["config", "get", "llm.api_key.nonexistent"])
    assert result.exit_code == 1


def test_doctor_fails_without_provider(fake_keyring, isolated_home):
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_doctor_passes_with_configured_provider(fake_keyring, isolated_home, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyTEST")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "doctor passed" in result.output
    assert "gemini" in result.output


def test_config_unset(fake_keyring, isolated_home):
    runner.invoke(app, ["config", "set", "llm.api_key.gemini", "AIzaSyTEST"])
    result = runner.invoke(app, ["config", "unset", "llm.api_key.gemini"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config", "get", "llm.api_key.gemini"])
    assert result.exit_code == 1
