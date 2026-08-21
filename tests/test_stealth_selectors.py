"""Unit tests for SelectorRegistry and BrowserSessionPool (UC-09 & UC-10)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from jobot.stealth.selectors import SelectorRegistry
from jobot.stealth.session_manager import BrowserSessionPool


def test_selector_registry_defaults():
    registry = SelectorRegistry()
    gh_selectors = registry.get_selectors("greenhouse", "first_name")
    assert len(gh_selectors) > 0
    assert "input#first_name" in gh_selectors

    lever_selectors = registry.get_selectors("lever", "email")
    assert len(lever_selectors) > 0


def test_selector_registry_custom_registration():
    registry = SelectorRegistry()
    registry.register("custom_ats", "custom_field", ["#primary", ".fallback-1", ".fallback-2"])
    selectors = registry.get_selectors("custom_ats", "custom_field")
    assert selectors == ["#primary", ".fallback-1", ".fallback-2"]


@pytest.mark.asyncio
async def test_selector_registry_self_healing_resolution():
    registry = SelectorRegistry()
    mock_page = MagicMock()

    # Primary selector is invisible, fallback selector is visible
    def mock_locator(selector: str):
        loc = MagicMock()
        first = MagicMock()
        if selector == "input#first_name":
            first.is_visible = AsyncMock(return_value=False)
        else:
            first.is_visible = AsyncMock(return_value=True)
        loc.first = first
        return loc

    mock_page.locator.side_effect = mock_locator

    resolved_loc, successful_sel = await registry.resolve_element(
        mock_page, "greenhouse", "first_name"
    )
    assert resolved_loc is not None
    assert successful_sel == "input[name='first_name']"


@pytest.mark.asyncio
async def test_browser_session_pool_lifecycle():
    pool = BrowserSessionPool()
    assert len(pool._pool) == 0
    await pool.close_all()
