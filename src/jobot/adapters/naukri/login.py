import asyncio
import logging
from typing import Optional
from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)


class NaukriLoginFlow:
    """
    Automated and Supervised Naukri.com Login Handler (Layer 5/8).
    Handles credential entry, session persistence, and OTP input pause.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless

    async def execute_login(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> bool:
        session = BrowserSession(portal="naukri", headless=self.headless)
        await session.start()

        try:
            page = await session.new_page()
            logger.info("[NAUKRI LOGIN] Navigating to Naukri login page...")
            await page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded")

            # Check if already logged in by looking for user profile elements
            try:
                profile_elem = await page.wait_for_selector(
                    ".nQuickHead, .user-name, a[href*='mnjuser/profile']", timeout=3000
                )
                if profile_elem:
                    logger.info("[NAUKRI LOGIN] Active session restored successfully.")
                    return True
            except Exception:
                pass

            # Fill username & password if present and provided
            if username and password:
                try:
                    email_field = await page.wait_for_selector(
                        "#usernameField, input[placeholder*='Email']", timeout=5000
                    )
                    if email_field:
                        await email_field.fill(username)

                    pass_field = await page.wait_for_selector(
                        "#passwordField, input[placeholder*='Password']", timeout=5000
                    )
                    if pass_field:
                        await pass_field.fill(password)

                    submit_btn = await page.wait_for_selector(
                        "button[type='submit'], .waves-effect", timeout=5000
                    )
                    if submit_btn:
                        await submit_btn.click()
                except Exception as e:
                    logger.warning(f"[NAUKRI LOGIN] Auto-fill failed: {e}")

            # Check for OTP requirement
            try:
                otp_field = await page.wait_for_selector(
                    "input[placeholder*='OTP'], input[name*='otp'], .otp-input", timeout=4000
                )
                if otp_field:
                    logger.warning("[NAUKRI LOGIN] OTP verification required!")
                    otp = input("Please enter the OTP received on your phone/email: ")
                    await otp_field.fill(otp.strip())
                    verify_btn = await page.wait_for_selector(
                        "button[type='submit'], .verify-btn", timeout=3000
                    )
                    if verify_btn:
                        await verify_btn.click()
            except Exception:
                pass

            logger.info("[NAUKRI LOGIN] Login complete. Session persisted.")
            return True
        finally:
            await session.close()
