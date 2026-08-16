"""Live Easy Apply saga test against the mock LinkedIn harness (Phase 3, T3.6).

Opt-in via JOBOT_RUN_LIVE_BROWSER=1 (requires patchright browsers installed).
"""

import os
import threading

import pytest
from jobot.stealth.browser import BrowserSession
from jobot.stealth.linkedin_easy_apply import EasyApplySaga
from jobot.models.domain import PersonalInfo, UserProfile

RUN_LIVE = os.getenv("JOBOT_RUN_LIVE_BROWSER") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_LIVE, reason="live browser test opt-in via JOBOT_RUN_LIVE_BROWSER=1"
)

HARNESS_PORT = 5801


@pytest.fixture(scope="module")
def harness_url():
    from tests.mock_linkedin.app import app

    server = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=HARNESS_PORT, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server.start()
    return f"http://127.0.0.1:{HARNESS_PORT}"


@pytest.mark.asyncio
async def test_live_easy_apply_against_mock_harness(harness_url):
    profile = UserProfile(
        profile_id="p_live",
        personal_info=PersonalInfo(
            first_name="Aryan", last_name="Sharma", email="aryan@example.com", phone="+911234567890"
        ),
        skills=["Python"],
    )
    browser = BrowserSession(portal="mock_linkedin_test", headless=True)
    await browser.start()
    try:
        saga = EasyApplySaga(browser)
        result = await saga.run(f"{harness_url}/job/1", profile)
        assert result.success is True
        assert result.status == "verify"
        assert len(result.evidence_shots) == 3
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_live_no_easy_apply_button(harness_url):
    profile = UserProfile(
        profile_id="p_live2",
        personal_info=PersonalInfo(first_name="Aryan", last_name="Sharma", email="a@b.com"),
        skills=[],
    )
    browser = BrowserSession(portal="mock_linkedin_test2", headless=True)
    await browser.start()
    try:
        saga = EasyApplySaga(browser)
        result = await saga.run(f"{harness_url}/job/no_easy_apply", profile)
        assert result.success is False
        assert "No Easy Apply button" in result.reason
    finally:
        await browser.close()
