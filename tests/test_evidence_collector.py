"""Unit tests for BrowserEvidenceCollector (UC-11)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from jobot.obs.evidence import BrowserEvidenceCollector


@pytest.mark.asyncio
async def test_evidence_collector_flow(tmp_path: Path):
    collector = BrowserEvidenceCollector(base_dir=tmp_path / "evidence")

    mock_page = MagicMock()
    mock_page.content = AsyncMock(return_value="<html><body>Application Form</body></html>")
    mock_page.screenshot = AsyncMock()

    app_id = "test_app_123"
    site = "greenhouse"

    # Pre-submit capture
    pre = await collector.capture_pre_submit(mock_page, app_id, site)
    assert "dom_hash" in pre
    assert len(pre["dom_hash"]) == 64

    # Post-submit capture
    mock_page.content = AsyncMock(return_value="<html><body>Confirmation #ABC1234</body></html>")
    manifest = await collector.capture_post_submit(
        mock_page,
        app_id,
        site,
        confirmation_id="GH_CONF_9999",
        pre_evidence=pre,
    )

    assert manifest.application_id == app_id
    assert manifest.site == site
    assert manifest.confirmation_id == "GH_CONF_9999"
    assert manifest.pre_submit_dom_hash == pre["dom_hash"]
    assert manifest.post_submit_dom_hash is not None
    assert manifest.post_submit_dom_hash != pre["dom_hash"]

    # Verify manifest file exists on disk
    manifest_file = tmp_path / "evidence" / app_id / "manifest.json"
    assert manifest_file.exists()
