"""Git-based plugin installer with manifest validation and registration."""

import json
import logging
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    def __init__(self, plugins_dir: Optional[Path] = None) -> None:
        self.plugins_dir = Path(plugins_dir or (Path.home() / ".jobot" / "plugins"))
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.plugins_dir / "index.json"

    # -- index --------------------------------------------------------------

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_index(self, index: Dict[str, Any]) -> None:
        self.index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    def list_plugins(self) -> List[Dict[str, Any]]:
        index = self._load_index()
        return [dict(value, name=name) for name, value in index.items()]

    # -- install ------------------------------------------------------------

    @staticmethod
    def _as_git_url(url: str) -> str:
        if url.startswith("file:") or "://" in url:
            return url
        if ":" in url[:3] or "\\" in url:  # windows-style path
            return "file:///" + url.replace("\\", "/").replace(" ", "%20")
        return url

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
        cmd = ["git", "clone", "--depth", "1", self._as_git_url(url), str(dest)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise ValueError(f"git clone failed for '{url}': {proc.stderr.strip()[:300]}")

    # -- remove -------------------------------------------------------------

    def remove(self, name: str) -> bool:
        dest = self.plugins_dir / name
        index = self._load_index()
        if name not in index:
            return False
        if dest.exists():
            _force_remove(dest)
        index.pop(name, None)
        self._save_index(index)
        return True
