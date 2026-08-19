"""Browser Evidence Protocol (UC-11).

Captures, hashes, and persists deterministic pre-submission and post-submission
evidence (DOM HTML and screenshots) for non-repudiation and verification auditing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EvidenceManifest(BaseModel):
    application_id: str
    site: str
    pre_submit_dom_hash: str | None = None
    pre_submit_screenshot: str | None = None
    post_submit_dom_hash: str | None = None
    post_submit_screenshot: str | None = None
    confirmation_id: str | None = None
    api_request_payload_hash: str | None = None
    api_response_status: int | None = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BrowserEvidenceCollector:
    """Manages pre/post submit evidence artifacts for auditability."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path.home() / ".jobot" / "evidence"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_app_dir(self, application_id: str) -> Path:
        app_dir = self.base_dir / application_id
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    def record_api_evidence(
        self,
        application_id: str,
        site: str,
        confirmation_id: str | None = None,
        request_payload: bytes | None = None,
        response_status: int | None = None,
    ) -> EvidenceManifest:
        """Record non-repudiation manifest for direct HTTP API submissions."""
        app_dir = self.get_app_dir(application_id)
        req_hash = (
            hashlib.sha256(request_payload).hexdigest() if request_payload is not None else None
        )
        if request_payload is not None:
            (app_dir / "api_request.json").write_bytes(request_payload)

        manifest = EvidenceManifest(
            application_id=application_id,
            site=site,
            confirmation_id=confirmation_id,
            api_request_payload_hash=req_hash,
            api_response_status=response_status,
        )

        manifest_file = app_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")
        return manifest

    async def capture_pre_submit(self, page: Any, application_id: str, site: str) -> dict[str, str]:
        """Capture pre-submit screenshot and DOM snapshot."""
        app_dir = self.get_app_dir(application_id)
        screenshot_path = app_dir / "pre_submit.png"
        dom_path = app_dir / "pre_submit.html"

        # Capture screenshot if page provides screenshot method
        if hasattr(page, "screenshot"):
            try:
                await page.screenshot(path=str(screenshot_path))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed pre-submit screenshot: %s", exc)

        dom_html = ""
        if hasattr(page, "content"):
            try:
                dom_html = await page.content()
                dom_path.write_text(dom_html, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed pre-submit DOM capture: %s", exc)

        dom_hash = hashlib.sha256(dom_html.encode("utf-8")).hexdigest() if dom_html else ""

        return {
            "screenshot": str(screenshot_path) if screenshot_path.exists() else "",
            "dom_path": str(dom_path) if dom_path.exists() else "",
            "dom_hash": dom_hash,
        }

    async def capture_post_submit(
        self,
        page: Any,
        application_id: str,
        site: str,
        confirmation_id: str | None = None,
        pre_evidence: dict[str, str] | None = None,
    ) -> EvidenceManifest:
        """Capture post-submit screenshot and DOM snapshot, save manifest."""
        app_dir = self.get_app_dir(application_id)
        screenshot_path = app_dir / "post_submit.png"
        dom_path = app_dir / "post_submit.html"

        if hasattr(page, "screenshot"):
            try:
                await page.screenshot(path=str(screenshot_path))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed post-submit screenshot: %s", exc)

        dom_html = ""
        if hasattr(page, "content"):
            try:
                dom_html = await page.content()
                dom_path.write_text(dom_html, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed post-submit DOM capture: %s", exc)

        dom_hash = hashlib.sha256(dom_html.encode("utf-8")).hexdigest() if dom_html else ""

        pre = pre_evidence or {}
        manifest = EvidenceManifest(
            application_id=application_id,
            site=site,
            pre_submit_dom_hash=pre.get("dom_hash"),
            pre_submit_screenshot=pre.get("screenshot"),
            post_submit_dom_hash=dom_hash,
            post_submit_screenshot=str(screenshot_path) if screenshot_path.exists() else None,
            confirmation_id=confirmation_id,
        )

        manifest_file = app_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")
        return manifest


__all__ = ["BrowserEvidenceCollector", "EvidenceManifest"]
