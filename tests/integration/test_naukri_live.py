"""P1.1/P1.2 live browser test — honest Naukri submit/verify against a mock harness.

Opt-in via JOBOT_RUN_LIVE_BROWSER=1 (requires patchright browsers installed).
"""

import os
import threading

import pytest
from jobot.adapters.naukri import verify as verify_module
from jobot.adapters.naukri.submit import NaukriSubmitter
from jobot.adapters.naukri.verify import NaukriVerifier
from jobot.models.domain import Application
from jobot.stealth.browser import BrowserSession

RUN_LIVE = os.getenv("JOBOT_RUN_LIVE_BROWSER") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_LIVE, reason="live browser test opt-in via JOBOT_RUN_LIVE_BROWSER=1"
)

HARNESS_PORT = 5802

JOB_HTML = """
<!DOCTYPE html>
<html><body>
<h1 class="jd-header-title">Senior Backend Engineer</h1>
<button class="apply-button" onclick="document.getElementById('status').innerText='Your application has been submitted'">Apply Now</button>
<div id="status"></div>
</body></html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html><body>
<h1>My Applications</h1>
<div class="application-row">Senior Backend Engineer — job-101 — Applied on 15 Aug 2026</div>
</body></html>
"""


@pytest.fixture(scope="module")
def harness_url():
    from flask import Flask

    app = Flask(__name__)

    @app.route("/job")
    def job_page():
        return JOB_HTML

    @app.route("/myapplications")
    def dashboard():
        return DASHBOARD_HTML

    server = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=HARNESS_PORT, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server.start()
    return f"http://127.0.0.1:{HARNESS_PORT}"


@pytest.mark.asyncio
async def test_live_submit_confirms_then_verify_finds(harness_url, monkeypatch):
    application = Application(
        application_id="app_live_nk",
        job_id="job-101",
        site="naukri",
        idempotency_key="key_live_nk",
        job_url=f"{harness_url}/job",
    )
    browser = BrowserSession(portal="naukri_live_test", headless=True)
    await browser.start()
    try:
        page = await browser.new_page()
        submitter = NaukriSubmitter()
        ok = await submitter.submit(application, page=page)
        assert ok is True

        monkeypatch.setattr(verify_module, "DASHBOARD_URL", f"{harness_url}/myapplications")
        result = await NaukriVerifier().verify(application, page=page)
        assert result.success is True
        assert result.confirmation_id == "job-101"
    finally:
        await browser.close()


@pytest.mark.asyncio
async def test_live_submit_no_button_fails_honestly(harness_url):
    from flask import Flask

    no_button = Flask("no_button")

    @no_button.route("/job")
    def job_page():
        return "<html><body><h1>Job expired</h1></body></html>"

    server = threading.Thread(
        target=lambda: no_button.run(
            host="127.0.0.1", port=HARNESS_PORT + 1, debug=False, use_reloader=False
        ),
        daemon=True,
    )
    server.start()

    application = Application(
        application_id="app_live_nk2",
        job_id="job-999",
        site="naukri",
        idempotency_key="key_live_nk2",
        job_url=f"http://127.0.0.1:{HARNESS_PORT + 1}/job",
    )
    browser = BrowserSession(portal="naukri_live_test2", headless=True)
    await browser.start()
    try:
        page = await browser.new_page()
        ok = await NaukriSubmitter().submit(application, page=page)
        assert ok is False
    finally:
        await browser.close()
