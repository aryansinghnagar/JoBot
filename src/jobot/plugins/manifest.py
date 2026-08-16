"""PluginManifest schema + loader (validated from jobot-manifest.yaml)."""

import re
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

MANIFEST_FILENAME = "jobot-manifest.yaml"

# Permissions a plugin may declare. Anything else is rejected at install.
ALLOWED_PERMISSIONS = {
    "network",
    "filesystem",
    "browser",
    "email",
    "scheduler",
    "llm",
    "storage",
}

# Entrypoint functions may not live in these modules (no access to internals).
FORBIDDEN_MODULES = {"jobot.storage.vault", "jobot.secrets", "jobot.config"}

# Packages a plugin may declare in `requires` without special review.
ALLOWED_REQUIRES = {
    "requests",
    "httpx",
    "jinja2",
    "pyyaml",
    "pydantic",
    "rich",
    "pandas",
    "numpy",
}

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class PluginEntrypoint(BaseModel):
    name: str
    module: str
    function: str

    @field_validator("module")
    @classmethod
    def _module_not_forbidden(cls, value: str) -> str:
        if value in FORBIDDEN_MODULES or value.startswith("jobot."):
            raise ValueError(f"entrypoint module '{value}' is not permitted")
        return value

    @field_validator("function")
    @classmethod
    def _function_valid(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", value):
            raise ValueError(f"invalid function name '{value}'")
        return value


class PluginManifest(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    requires: List[str] = []
    permissions: List[str] = []
    entrypoints: List[PluginEntrypoint] = []

    @field_validator("name")
    @classmethod
    def _name_safe(cls, value: str) -> str:
        if not _NAME_RE.match(value):
            raise ValueError(
                f"invalid plugin name '{value}': lowercase alnum, dash/underscore, no path separators"
            )
        return value

    @field_validator("version")
    @classmethod
    def _version_semver(cls, value: str) -> str:
        if not _VERSION_RE.match(value):
            raise ValueError(f"invalid version '{value}': semver x.y.z required")
        return value

    @field_validator("permissions")
    @classmethod
    def _permissions_known(cls, values: List[str]) -> List[str]:
        unknown = set(values) - ALLOWED_PERMISSIONS
        if unknown:
            raise ValueError(
                f"unknown permission(s) {sorted(unknown)}; allowed: {sorted(ALLOWED_PERMISSIONS)}"
            )
        return list(dict.fromkeys(values))

    @field_validator("requires")
    @classmethod
    def _requires_known(cls, values: List[str]) -> List[str]:
        unknown = set(values) - ALLOWED_REQUIRES
        if unknown:
            raise ValueError(
                f"unvetted dependency(s) {sorted(unknown)}; allowed: {sorted(ALLOWED_REQUIRES)}"
            )
        return list(dict.fromkeys(values))

    def entrypoint_names(self) -> List[str]:
        return [e.name for e in self.entrypoints]


def load_manifest(repo_path: Path) -> PluginManifest:
    """Load + validate the manifest file from a plugin repo root."""
    manifest_path = Path(repo_path) / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise ValueError(f"missing {MANIFEST_FILENAME} in plugin repo")
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{MANIFEST_FILENAME} must contain a mapping")
    return PluginManifest(**raw)


def manifest_is_valid(manifest: PluginManifest) -> bool:
    return bool(manifest.entrypoints or manifest.permissions)
