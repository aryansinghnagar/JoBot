"""Git-based plugin installer with manifest validation and registration."""

import json
import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from jobot.plugins.manifest import PluginManifest, load_manifest

logger = logging.getLogger(__name__)

DEFAULT_PLUGINS_DIR = Path.home() / ".jobot" / "plugins"


def _force_remove(path: Path) -> None:
    """Remove a directory tree even with read-only files (git pack files on Windows)."""

    def _onerror(func: Any, target: str, exc_info: Any) -> None:
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        func(target)

    shutil.rmtree(path, onerror=_onerror)


class PluginInstaller:
    """Clones a plugin repo, validates its manifest, and registers it.

    Plugins land in `~/.jobot/plugins/<name>/` and are recorded in
    `index.json`. Names are validated against path-traversal patterns.
    """

    def __init__(self, plugins_dir: Path | None = None) -> None:
        self.plugins_dir = Path(plugins_dir or (Path.home() / ".jobot" / "plugins"))
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.plugins_dir / "index.json"

    # -- index --------------------------------------------------------------

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, index: dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def list_plugins(self) -> list[dict[str, Any]]:
        index = self._load_index()
        return [dict(value, name=name) for name, value in index.items()]

    # Audit fix JOB-SEC-003: removed ``file`` from the default ALLOWED_SCHEMES.
    # The ``file://`` scheme allowed a local plugin path to be supplied as a
    # URL, which expands the attack surface (a malicious actor with write
    # access to a temp directory could swap the plugin source between clone
    # and copy). Plugins must come from a remote git host over
    # http/https/ssh/git — the four network-friendly git transports.
    #
    # The ``file`` scheme is still reachable from tests via the
    # ``JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL=1`` opt-in env var. Tests need to
    # install from a local ``git init`` fixture, but production users should
    # never be able to do this without explicitly setting the env var.
    DEFAULT_ALLOWED_SCHEMES = frozenset({"http", "https", "ssh", "git"})
    TEST_ALLOWED_SCHEMES = frozenset({"http", "https", "ssh", "git", "file"})

    @property
    def ALLOWED_SCHEMES(self) -> frozenset[str]:
        import os as _os

        if _os.getenv("JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL") == "1":
            return self.TEST_ALLOWED_SCHEMES
        return self.DEFAULT_ALLOWED_SCHEMES

    @classmethod
    def _as_git_url(cls, url: str) -> str:
        import os as _os

        raw = url.strip()
        if raw.startswith("ext::") or "::" in raw:
            raise ValueError(f"Unsupported or unsafe git transport protocol in '{url}'")

        if raw.startswith("git@"):
            return raw

        # Determine the allowed-schemes set the same way the property does.
        # We cannot use the property here because ``_as_git_url`` is a
        # classmethod, so we duplicate the small env-var check.
        if _os.getenv("JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL") == "1":
            allowed = cls.TEST_ALLOWED_SCHEMES
        else:
            allowed = cls.DEFAULT_ALLOWED_SCHEMES

        if "://" in raw:
            scheme = raw.split("://", 1)[0].lower()
            if scheme not in allowed:
                raise ValueError(
                    f"Disallowed git URL scheme '{scheme}' in '{url}'. "
                    f"Allowed schemes: {sorted(allowed)}. "
                    f"(Audit fix JOB-SEC-003: 'file' scheme is only allowed when "
                    f"JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL=1 is set, which is intended "
                    f"for the test suite only.)"
                )
            return raw

        # Audit fix JOB-SEC-003: refuse bare local paths. Previously a path
        # like ``/tmp/evil/plugin`` or ``./my-plugin`` was silently coerced
        # into a ``file:///`` URL, which then ran ``git clone`` against a
        # local directory — bypassing the network-transport-only invariant.
        if raw.startswith("file:"):
            if "file" not in allowed:
                raise ValueError(
                    f"'file:' scheme is not allowed for plugin install (audit fix JOB-SEC-003): '{url}'. "
                    f"Set JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL=1 for test fixtures only."
                )
            return raw

        # Heuristic for windows-style paths (drive letter or backslashes).
        # These were previously silently coerced to ``file:///`` URLs — now
        # refused with a clear error message unless test mode is enabled.
        if "\\" in raw or (len(raw) >= 2 and raw[1] == ":"):
            if "file" not in allowed:
                raise ValueError(
                    f"Local paths are not allowed for plugin install (audit fix JOB-SEC-003): '{url}'. "
                    f"Use a remote git URL (https://, ssh://, git@) instead."
                )
            return "file:///" + raw.replace("\\", "/").replace(" ", "%20")

        # Otherwise treat as a relative URL: refuse (was previously returned
        # as-is, which ``git clone`` would interpret as a local path).
        if not any(raw.startswith(s + "://") for s in allowed) and not raw.startswith("git@"):
            raise ValueError(f"Plugin URL must use one of {sorted(allowed)} schemes: '{url}'")

        return raw

    def install(self, url: str) -> PluginManifest:
        with tempfile.TemporaryDirectory(prefix="jobot-plugin-") as tmp:
            clone_dir = Path(tmp) / "src"
            self._git_clone(url, clone_dir)
            manifest = load_manifest(clone_dir)

            dest = self.plugins_dir / manifest.name
            if dest.exists():
                raise ValueError(f"plugin '{manifest.name}' is already installed")

            shutil.copytree(clone_dir, dest)
            index = self._load_index()
            index[manifest.name] = {
                "version": manifest.version,
                "author": manifest.author,
                "license": manifest.license,
                "permissions": manifest.permissions,
                "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._save_index(index)
            logger.info("installed plugin %s@%s", manifest.name, manifest.version)
            return manifest

    def _git_clone(self, url: str, dest: Path) -> None:
        git_url = self._as_git_url(url)
        cmd = [
            "git",
            "-c",
            "protocol.ext.allow=never",
            "clone",
            "--depth",
            "1",
            git_url,
            str(dest),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise ValueError(f"git clone failed for '{url}': {proc.stderr.strip()[:300]}")

    def remove(self, name: str) -> bool:
        if not re.match(r"^[a-z0-9][a-z0-9_-]{1,63}$", name):
            raise ValueError(f"Invalid plugin name '{name}'")
        dest = self.plugins_dir / name
        index = self._load_index()
        if name not in index:
            return False
        if dest.exists():
            _force_remove(dest)
        index.pop(name, None)
        self._save_index(index)
        return True
