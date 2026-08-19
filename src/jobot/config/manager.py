"""Three-tier configuration manager (SETUP.md §3).

Tiers (highest precedence first):
  1. Environment (`JOBOT_<KEY>` for dotted keys, e.g. `llm.default_provider`
     -> `JOBOT_LLM_DEFAULT_PROVIDER`; legacy `JOBOT_DEFAULT_LLM_PROVIDER`
     also honored)
  2. OS keyring for secrets (`llm.api_key.*`, `board_cookies.*`,
     `board_password.*`, `smtp.*`) via `jobot.secrets`
  3. `~/.jobot/config.yaml` for non-secret values

`jobot config set` writes secrets to the keyring and everything else to
`config.yaml` — never edit files directly for secrets.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from jobot.secrets import delete_secret, get_secret, set_secret

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".jobot" / "config.yaml"

SECRET_PREFIXES = ("llm.api_key.", "board_cookies.", "board_password.", "smtp.")

LEGACY_LLM_PROVIDER_ENV = "JOBOT_DEFAULT_LLM_PROVIDER"


class ConfigManager:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load_file()

    def _load_file(self) -> None:
        if self.config_path.exists():
            try:
                raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
                if isinstance(raw, dict):
                    self._data = raw
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load config file %s: %s", self.config_path, exc)

    def _save_file(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml.safe_dump(self._data, sort_keys=False), encoding="utf-8")

    # -- key addressing -----------------------------------------------------

    @staticmethod
    def is_secret(key: str) -> bool:
        return any(key.startswith(prefix) for prefix in SECRET_PREFIXES)

    @staticmethod
    def env_name(key: str) -> str:
        return f"JOBOT_{key.upper().replace('.', '_')}"

    def _env_get(self, key: str) -> str | None:
        import os

        value = os.getenv(self.env_name(key))
        if value is not None:
            return value
        if key == "llm.default_provider":
            return os.getenv(LEGACY_LLM_PROVIDER_ENV)
        return None

    def _file_get(self, key: str) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def _file_set(self, key: str, value: Any) -> None:
        node: dict[str, Any] = self._data
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def _file_unset(self, key: str) -> None:
        node: Any = self._data
        parts = key.split(".")
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                return
            node = node[part]
        if isinstance(node, dict):
            node.pop(parts[-1], None)

    # -- public API ---------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        env_value = self._env_get(key)
        if env_value is not None:
            return env_value
        if self.is_secret(key):
            value = get_secret(key)
            return value if value is not None else default
        file_value = self._file_get(key)
        return file_value if file_value is not None else default

    def set(self, key: str, value: str) -> None:
        if self.is_secret(key):
            set_secret(key, value)
        else:
            self._file_set(key, value)
            self._save_file()

    def unset(self, key: str) -> None:
        if self.is_secret(key):
            delete_secret(key)
        else:
            self._file_unset(key)
            self._save_file()

    def all_keys(self) -> list[str]:
        keys: list[str] = []

        def walk(node: Any, prefix: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{prefix}.{k}" if prefix else k)
            else:
                keys.append(prefix)

        walk(self._data, "")
        for key in ("smtp.user", "smtp.password", "board_cookies.linkedin"):
            if get_secret(key):
                keys.append(key)
        for name in (
            "gemini",
            "openai",
            "anthropic",
            "openrouter",
            "groq",
            "together",
            "ollama",
            "vllm",
            "mistral",
            "cohere",
            "bedrock",
            "vertex",
        ):
            if get_secret(f"llm.api_key.{name}"):
                keys.append(f"llm.api_key.{name}")
        return sorted(set(keys))

    def show_masked(self) -> dict[str, str]:
        from jobot.secrets import mask

        out: dict[str, str] = {}
        for key in self.all_keys():
            value = self.get(key)
            if value is None:
                continue
            out[key] = mask(str(value)) if self.is_secret(key) else str(value)
        return out
