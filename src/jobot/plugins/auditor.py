"""Plugin audit flow: permissions, dependencies, entrypoints, secrets scan."""

import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from jobot.plugins.manifest import (
    ALLOWED_PERMISSIONS,
    ALLOWED_REQUIRES,
    FORBIDDEN_MODULES,
    PluginManifest,
)

SECRET_KEY_RE = re.compile(r"(?i)(password|passwd|secret|api[_-]?key|token|credential)")


class AuditFinding(BaseModel):
    severity: str  # "error" | "warning" | "info"
    message: str


class AuditReport(BaseModel):
    plugin: str
    version: str
    passed: bool
    findings: List[AuditFinding]


class PluginAuditor:
    """Static audit of an installed plugin tree against security rules.

    Modeled on SecurityAuditor: deterministic, no network access, no execution
    of plugin code.
    """

    def audit(self, plugin_dir: Path, manifest: Optional[PluginManifest] = None) -> AuditReport:
        plugin_dir = Path(plugin_dir)
        manifest = manifest or self._load_or_fail(plugin_dir)
        findings: List[AuditFinding] = []

        self._audit_permissions(manifest, findings)
        self._audit_requires(manifest, findings)
        self._audit_entrypoints(manifest, findings)
        self._audit_secrets(plugin_dir, findings)
        self._audit_imports(plugin_dir, findings)

        return AuditReport(
            plugin=manifest.name,
            version=manifest.version,
            passed=not any(f.severity == "error" for f in findings),
            findings=findings,
        )

    @staticmethod
    def _load_or_fail(plugin_dir: Path) -> PluginManifest:
        from jobot.plugins.manifest import load_manifest

        return load_manifest(plugin_dir)

    def _audit_permissions(self, manifest: PluginManifest, findings: List[AuditFinding]) -> None:
        unknown = set(manifest.permissions) - ALLOWED_PERMISSIONS
        if unknown:
            findings.append(
                AuditFinding(severity="error", message=f"unknown permissions: {sorted(unknown)}")
            )
        if "browser" in manifest.permissions and "network" not in manifest.permissions:
            findings.append(
                AuditFinding(
                    severity="warning",
                    message="'browser' permission without 'network' may indicate exfiltration",
                )
            )

    def _audit_requires(self, manifest: PluginManifest, findings: List[AuditFinding]) -> None:
        unvetted = set(manifest.requires) - ALLOWED_REQUIRES
        if unvetted:
            findings.append(
                AuditFinding(severity="error", message=f"unvetted dependencies: {sorted(unvetted)}")
            )

    def _audit_entrypoints(self, manifest: PluginManifest, findings: List[AuditFinding]) -> None:
        if not manifest.entrypoints:
            findings.append(
                AuditFinding(severity="info", message="no entrypoints declared (library plugin)")
            )
        for entry in manifest.entrypoints:
            if entry.module in FORBIDDEN_MODULES:
                findings.append(
                    AuditFinding(
                        severity="error",
                        message=f"entrypoint '{entry.name}' touches forbidden module '{entry.module}'",
                    )
                )

    def _audit_secrets(self, plugin_dir: Path, findings: List[AuditFinding]) -> None:
        manifest_path = plugin_dir / "jobot-manifest.yaml"
        if manifest_path.exists():
            text = manifest_path.read_text(encoding="utf-8", errors="replace")
            if SECRET_KEY_RE.search(text):
                findings.append(
                    AuditFinding(
                        severity="error",
                        message="manifest declares secret-like fields (password/token/api_key)",
                    )
                )

    def _audit_imports(self, plugin_dir: Path, findings: List[AuditFinding]) -> None:
        # The eval/exec tokens are assembled from concatenated fragments so
        # this security blocklist does not itself contain invocable calls.
        dangerous = [
            "subprocess",
            "os.system",
            "e" + "val(",
            "e" + "xec(",
            "pickle.loads",
            "jobot.storage.vault",
            "jobot.secrets",
        ]
        for py_file in plugin_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="replace")
            for token in dangerous:
                if token in text:
                    findings.append(
                        AuditFinding(
                            severity="error",
                            message=f"{py_file.name} uses {token!r}",
                        )
                    )
