"""Shared environment diagnostics — single source of truth for `jobot doctor`
(CLI) and the GUI sidecar `doctor` RPC method.
"""

import asyncio
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from jobot.config.profile import load_llm_settings
from jobot.documents import pdftotext_available, tex_engine_available
from jobot.llm.providers import PROVIDER_REGISTRY
from jobot.llm.router import ModelRouter
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault


class DoctorCheck(BaseModel):
    label: str
    ok: bool
    detail: str = ""
    warn: bool = False


class DoctorReport(BaseModel):
    checks: list[DoctorCheck]
    providers: list[dict[str, Any]]
    all_ok: bool


def _profile_exists() -> bool:
    return (Path.home() / ".jobot" / "profiles" / "default.enc").exists()


def run_doctor_checks() -> DoctorReport:
    """Run all doctor checks and return a structured report (never raises)."""
    checks: list[DoctorCheck] = []

    py_ok = sys.version_info >= (3, 11)
    checks.append(DoctorCheck(label="Python >= 3.11", ok=py_ok, detail=sys.version.split()[0]))

    try:
        import keyring

        backend = keyring.get_keyring()
        backend_name = backend.__class__.__name__
        keyring_ok = "fail" not in backend_name.lower() and "null" not in backend_name.lower()
        checks.append(DoctorCheck(label="OS keyring", ok=keyring_ok, detail=backend_name))
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck(label="OS keyring", ok=False, detail=str(exc)))

    try:
        db = DatabaseManager()
        checks.append(DoctorCheck(label="SQLite database", ok=True, detail=str(db.db_path)))
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck(label="SQLite database", ok=False, detail=str(exc)))

    try:
        vault = CredentialVault()
        checks.append(DoctorCheck(label="Encryption vault", ok=True, detail=str(vault.key_dir)))
    except Exception as exc:  # noqa: BLE001
        checks.append(DoctorCheck(label="Encryption vault", ok=False, detail=str(exc)))

    profile_ok = _profile_exists()
    checks.append(
        DoctorCheck(
            label="Profile (encrypted)",
            ok=profile_ok,
            detail=str(Path.home() / ".jobot" / "profiles" / "default.enc")
            if profile_ok
            else "missing - run 'jobot profile init'",
            warn=True,
        )
    )

    engine_ok = tex_engine_available()
    checks.append(
        DoctorCheck(
            label="LaTeX engine (lualatex/xelatex)",
            ok=True,
            detail="available" if engine_ok else "not found - reportlab fallback will be used",
        )
    )
    poppler_ok = pdftotext_available()
    checks.append(
        DoctorCheck(
            label="pdftotext (poppler)",
            ok=True,
            detail="available" if poppler_ok else "not found - pdfminer fallback will be used",
        )
    )
    checks.append(
        DoctorCheck(
            label="PDF rendering", ok=True, detail="reportlab (pure python) always available"
        )
    )

    router = ModelRouter(daily_budget_usd=load_llm_settings().daily_cost_cap_usd)
    provider_rows: list[dict[str, Any]] = []
    for name in PROVIDER_REGISTRY:
        configured = name in router.list_configured_providers()
        reachable = asyncio.run(router.health_check(name)) if configured else False
        detail = (
            "configured + reachable"
            if reachable
            else ("configured" if configured else "not configured")
        )
        provider_rows.append({"name": name, "ok": configured and reachable, "detail": detail})

    any_provider = any(row["ok"] for row in provider_rows)
    checks.append(
        DoctorCheck(
            label="LLM provider (>= 1 configured)",
            ok=any_provider,
            detail=f"{sum(1 for row in provider_rows if row['ok'])}/{len(provider_rows)}",
        )
    )

    all_ok = all(check.ok for check in checks if not check.warn)
    return DoctorReport(checks=checks, providers=provider_rows, all_ok=all_ok)


def export_diagnostic_bundle(output_path: Path | None = None) -> Path:
    """Create a redacted diagnostic zip archive for troubleshooting."""
    import json
    import platform
    import zipfile
    from datetime import datetime

    from jobot.adapters import AdapterRegistry
    from jobot.stealth.site_health import SiteHealthMonitor

    if output_path is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        export_dir = Path.home() / ".jobot" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        output_path = export_dir / f"jobot_diagnostics_{timestamp}.zip"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    report = run_doctor_checks()
    monitor = SiteHealthMonitor()
    sites = AdapterRegistry.list_supported_sites()

    site_health_data = [
        {
            "site": s,
            "status": monitor.get_status(s).status,
            "success_count": monitor.get_status(s).success_count,
            "failure_count": monitor.get_status(s).failure_count,
            "success_rate": monitor.get_status(s).success_rate,
            "avg_latency_ms": monitor.get_status(s).avg_latency_ms,
        }
        for s in sites
    ]

    system_info = {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": sys.version.split()[0],
        "generated_at": datetime.now(UTC).isoformat(),
    }

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("doctor_report.json", json.dumps(report.model_dump(), indent=2))
        zf.writestr("site_health.json", json.dumps(site_health_data, indent=2))
        zf.writestr("system_info.json", json.dumps(system_info, indent=2))

    return output_path
