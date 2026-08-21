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

Phase P2: ``get()`` results are cached with a 30s TTL so repeated lookups
for the same key (e.g. ``llm.default_provider`` checked on every router
call) skip the keyring / YAML-parse cost. The cache is invalidated on
file modification (Phase P6: ``watchdog`` observer) and on explicit
``set()`` / ``unset()`` writes.

Phase P6: ``ConfigManager`` starts a ``watchdog`` observer on
``config_path.parent`` so edits to ``config.yaml`` are picked up without
a process restart. The observer is opt-out (``watch=False``) for tests
and short-lived CLI invocations.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any

import yaml

from jobot.secrets import delete_secret, get_secret, set_secret

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".jobot" / "config.yaml"

SECRET_PREFIXES = ("llm.api_key.", "board_cookies.", "board_password.", "smtp.")

LEGACY_LLM_PROVIDER_ENV = "JOBOT_DEFAULT_LLM_PROVIDER"

# Phase P2: TTL for the ``get()`` result cache. 30s balances freshness
# (rotated secrets propagate within half a minute) against keyring call
# cost (a single ``get_secret`` round-trip can be ~50ms on macOS, ~5ms
# on Linux; the router calls ``get`` on every LLM request).
_CONFIG_CACHE_TTL_S = 30.0


class ConfigManager:
    def __init__(self, config_path: Path | None = None, *, watch: bool = False) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        # Phase P2: per-key TTL cache. Maps ``key`` -> ``(value, expires_at)``.
        # ``expires_at`` is a ``time.monotonic()`` deadline. Reads check the
        # deadline; writes (``set`` / ``unset``) clear the entire cache
        # because changing one key may invalidate derived lookups elsewhere.
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_lock = threading.Lock()
        self._load_file()
        # Phase P6: optional filesystem watcher. Disabled by default — tests
        # and short-lived CLI invocations do not need hot reload. The
        # long-running sidecar enables it via ``watch=True``.
        self._observer: Any = None
        if watch:
            self._start_watcher()

    def _load_file(self) -> None:
        if self.config_path.exists():
            try:
                raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
                if isinstance(raw, dict):
                    self._data = raw
            except (OSError, yaml.YAMLError, UnicodeDecodeError) as exc:  # noqa: BLE001
                # Phase B3 (JOB-ARC-002): narrowed from bare ``Exception`` to
                # the concrete failure modes of reading + parsing a YAML
                # config file. ``OSError`` covers filesystem / permission
                # issues, ``yaml.YAMLError`` covers YAML syntax errors, and
                # ``UnicodeDecodeError`` covers non-UTF-8 file content.
                logger.debug(
                    "Failed to load config file %s: %s", self.config_path, exc, exc_info=True
                )
        # Phase P2: invalidate the cache on every file (re)load — the
        # in-memory ``_data`` snapshot is now authoritative.
        with self._cache_lock:
            self._cache.clear()

    def _save_file(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(yaml.safe_dump(self._data, sort_keys=False), encoding="utf-8")
        # Phase P2: clear the cache so subsequent ``get`` calls re-read the
        # new value (we cannot rely on the watchdog observer to pick this
        # up fast enough — set() callers expect immediate consistency).
        with self._cache_lock:
            self._cache.clear()

    # -- Phase P6: filesystem watcher --------------------------------------

    def _start_watcher(self) -> None:
        """Start a ``watchdog`` observer on ``config_path.parent`` so edits
        to ``config.yaml`` trigger ``_load_file()`` automatically. The
        observer runs in its own thread and lives for the lifetime of the
        process. ``watchdog`` is an optional dependency (declared in
        ``[dev]`` extras); if it is not installed the watcher is a no-op
        and ``ConfigManager`` falls back to manual ``_load_file()`` calls
        on ``set`` / ``unset`` only.
        """
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:  # pragma: no cover — watchdog is a dev dep
            logger.debug(
                "watchdog not installed; config hot-reload disabled. "
                "Install with `pip install watchdog` to enable."
            )
            return

        manager = self

        class _ConfigReloadHandler(FileSystemEventHandler):  # type: ignore[misc]
            def on_modified(self, event: Any) -> None:
                if (
                    not event.is_directory
                    and Path(event.src_path).resolve() == manager.config_path.resolve()
                ):
                    logger.debug("config.yaml modified externally — reloading")
                    manager._load_file()

        observer = Observer()
        observer.daemon = True
        observer.schedule(
            _ConfigReloadHandler(),
            str(self.config_path.parent),
            recursive=False,
        )
        observer.start()
        self._observer = observer

    def stop_watcher(self) -> None:
        """Stop the filesystem watcher (if running). Safe to call multiple
        times or when no watcher was started."""
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception as exc:  # noqa: BLE001 — best-effort cleanup
                logger.debug("stop_watcher cleanup error: %s", exc)
            self._observer = None

    def __del__(self) -> None:
        # Best-effort cleanup — never raise from __del__.
        try:
            self.stop_watcher()
        except Exception as exc:  # noqa: BLE001
            logger.debug("__del__ watcher cleanup error: %s", exc)

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
        # Phase P2: TTL cache. Env-var lookups are already O(1) but
        # ``get_secret`` (keyring) can be ~50ms on macOS and the router
        # calls ``get("llm.default_provider")`` on every LLM request.
        # Caching for 30s cuts the keyring cost from N×50ms to 50ms for
        # any burst of N calls within the TTL window. Cache misses fall
        # through to the existing env / keyring / file lookup chain.
        now = time.monotonic()
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is not None and entry[1] > now:
                return entry[0]
        env_value = self._env_get(key)
        if env_value is not None:
            with self._cache_lock:
                self._cache[key] = (env_value, now + _CONFIG_CACHE_TTL_S)
            return env_value
        if self.is_secret(key):
            value = get_secret(key)
            result = value if value is not None else default
            with self._cache_lock:
                self._cache[key] = (result, now + _CONFIG_CACHE_TTL_S)
            return result
        file_value = self._file_get(key)
        result = file_value if file_value is not None else default
        with self._cache_lock:
            self._cache[key] = (result, now + _CONFIG_CACHE_TTL_S)
        return result

    def set(self, key: str, value: str) -> None:
        if self.is_secret(key):
            set_secret(key, value)
        else:
            self._file_set(key, value)
            self._save_file()
        # Phase P2: invalidate the cached value for this key so the next
        # ``get`` reflects the new value immediately.
        with self._cache_lock:
            self._cache.pop(key, None)

    def unset(self, key: str) -> None:
        if self.is_secret(key):
            delete_secret(key)
        else:
            self._file_unset(key)
            self._save_file()
        # Phase P2: invalidate the cached value for this key.
        with self._cache_lock:
            self._cache.pop(key, None)

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
