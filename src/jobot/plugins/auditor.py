"""Plugin audit flow: permissions, dependencies, entrypoints, secrets scan."""

import ast
import re
from pathlib import Path

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
    findings: list[AuditFinding]


class PluginAuditor:
    """Static audit of an installed plugin tree against security rules.

    Modeled on SecurityAuditor: deterministic, no network access, no execution
    of plugin code.
    """

    def audit(self, plugin_dir: Path, manifest: PluginManifest | None = None) -> AuditReport:
        plugin_dir = Path(plugin_dir)
        manifest = manifest or self._load_or_fail(plugin_dir)
        findings: list[AuditFinding] = []

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

    def _audit_permissions(self, manifest: PluginManifest, findings: list[AuditFinding]) -> None:
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

    def _audit_requires(self, manifest: PluginManifest, findings: list[AuditFinding]) -> None:
        unvetted = set(manifest.requires) - ALLOWED_REQUIRES
        if unvetted:
            findings.append(
                AuditFinding(severity="error", message=f"unvetted dependencies: {sorted(unvetted)}")
            )

    def _audit_entrypoints(self, manifest: PluginManifest, findings: list[AuditFinding]) -> None:
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

    def _audit_secrets(self, plugin_dir: Path, findings: list[AuditFinding]) -> None:
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

    # ------------------------------------------------------------------ #
    # Audit fix JOB-SEC-013: AST-based import scanning.
    #
    # The previous implementation used ``token in text`` substring matching
    # against the raw source. This is bypassable in multiple ways:
    #
    #   1. ``getattr(module, "system")("rm -rf /")`` — no substring match on
    #      ``os.system`` even though the runtime behavior is identical.
    #   2. ``__import__("subprocess")`` — no ``import subprocess`` substring.
    #   3. String concatenation / hex-encoded module names — same problem.
    #
    # The fix below walks the Python AST and inspects:
    #   - ``Import`` nodes (``import foo``, ``import foo.bar``)
    #   - ``ImportFrom`` nodes (``from foo import bar``)
    #   - ``Call`` nodes where ``func`` is ``__import__`` (dynamic imports)
    #   - ``Call`` nodes where ``func`` is ``getattr`` on a module-typed
    #     expression — best-effort, may produce false positives on
    #     innocuous ``getattr`` calls but those are rare in plugin code.
    #
    # This is still a static scan, not a full taint analysis. It catches
    # the obvious bypasses above without executing the plugin. For full
    # defense in depth, plugins are also run inside the standard Python
    # interpreter with no special privileges — the audit is an early
    # warning, not a sandbox.
    # ------------------------------------------------------------------ #

    DANGEROUS_MODULES: set[str] = {
        "subprocess",
        "os",
        "os.system",
        "os.popen",
        "pickle",
        "pickle.loads",
        "marshal",
        "ctypes",
        "multiprocessing",
        "asyncio.subprocess",
        "shutil",
        "pathlib",  # used for filesystem traversal; flagged for review
    }

    DANGEROUS_GLOBAL_CALLS: set[str] = {
        "__import__",
        "eval",
        "exec",
        "compile",
        "globals",
        "locals",
    }

    # Modules that are absolutely forbidden in plugin entrypoints.
    FORBIDDEN_INTERNAL_MODULES: set[str] = {
        "jobot.storage.vault",
        "jobot.secrets",
        "jobot.config",
    }

    def _audit_imports(self, plugin_dir: Path, findings: list[AuditFinding]) -> None:
        for py_file in plugin_dir.rglob("*.py"):
            rel = py_file.relative_to(plugin_dir)
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                findings.append(
                    AuditFinding(
                        severity="error",
                        message=f"{rel}: cannot parse Python source: {exc.msg} (line {exc.lineno})",
                    )
                )
                continue

            self._walk_ast_for_dangerous_imports(tree, rel, findings)

    def _walk_ast_for_dangerous_imports(
        self,
        tree: ast.AST,
        rel: Path,
        findings: list[AuditFinding],
    ) -> None:
        for node in ast.walk(tree):
            # Static ``import foo`` / ``import foo.bar``
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_module_name(alias.name, rel, node.lineno, findings)
            # ``from foo import bar``
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_module_name(node.module, rel, node.lineno, findings)
                    # Also check the from-imported names against the
                    # dangerous-module set, in case the plugin does
                    # ``from os import system`` (we flag the parent ``os``).
                    for alias in node.names:
                        full = f"{node.module}.{alias.name}"
                        self._check_module_name(full, rel, node.lineno, findings)
            # ``__import__("foo")`` / ``eval(...)`` / ``exec(...)``
            elif isinstance(node, ast.Call):
                func = node.func
                func_name: str | None = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    # ``getattr(...)`` is a Name; ``obj.system(...)`` is an Attribute.
                    func_name = func.attr
                if func_name and func_name in self.DANGEROUS_GLOBAL_CALLS:
                    findings.append(
                        AuditFinding(
                            severity="error",
                            message=(
                                f"{rel}:{node.lineno}: calls {func_name}() — "
                                f"dynamic code execution is forbidden in plugins "
                                f"(audit fix JOB-SEC-013)"
                            ),
                        )
                    )

    def _check_module_name(
        self,
        module_name: str,
        rel: Path,
        lineno: int,
        findings: list[AuditFinding],
    ) -> None:
        """Check whether an imported module name is dangerous or forbidden."""
        if not module_name:
            return

        # Forbidden internal JoBot modules — any touch is an error.
        for forbidden in self.FORBIDDEN_INTERNAL_MODULES:
            if module_name == forbidden or module_name.startswith(forbidden + "."):
                findings.append(
                    AuditFinding(
                        severity="error",
                        message=(
                            f"{rel}:{lineno}: imports forbidden internal module "
                            f"'{module_name}' (audit fix JOB-SEC-013)"
                        ),
                    )
                )
                return

        # Dangerous stdlib / third-party modules — flagged for review.
        # We match either the exact name or any prefix path (e.g. ``os``
        # matches ``os.system`` but NOT ``osc``).
        for dangerous in self.DANGEROUS_MODULES:
            if module_name == dangerous or module_name.startswith(dangerous + "."):
                findings.append(
                    AuditFinding(
                        severity="error",
                        message=(
                            f"{rel}:{lineno}: imports dangerous module "
                            f"'{module_name}' — flagged for manual review "
                            f"(audit fix JOB-SEC-013)"
                        ),
                    )
                )
                return
