"""Phase 4 WS6: PluginInstaller + PluginManifest + audit flow."""

from jobot.plugins.auditor import AuditReport, PluginAuditor
from jobot.plugins.installer import PluginInstaller
from jobot.plugins.manifest import (
    ALLOWED_PERMISSIONS,
    PluginEntrypoint,
    PluginManifest,
    load_manifest,
)

__all__ = [
    "AuditReport",
    "PluginAuditor",
    "PluginInstaller",
    "PluginEntrypoint",
    "PluginManifest",
    "load_manifest",
    "ALLOWED_PERMISSIONS",
]
