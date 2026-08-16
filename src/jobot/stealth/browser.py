from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import logging
from patchright.async_api import async_playwright, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    Manages a persistent Patchright browser session per portal (Layer 8).
    Persists cookies, storage state, and browser context across automation runs.
    """

    def __init__(
        self,
        portal: str = "default",
        headless: bool = True,
        proxy_config: Optional[Dict[str, Any]] = None,
        session_dir: Optional[Path] = None,
    ):
        self.portal = portal
        self.headless = headless
        self.proxy_config = proxy_config
        if session_dir is None:
            session_dir = Path.home() / ".jobot" / "sessions" / portal
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None

    async def start(self) -> "BrowserSession":
        """Launch Patchright persistent browser context with stealth parameters."""
        self.playwright = await async_playwright().start()

        kwargs: Dict[str, Any] = {
            "user_data_dir": str(self.session_dir),
            "headless": self.headless,
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "Asia/Kolkata",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            "ignore_default_args": ["--enable-automation"],
        }
        if self.proxy_config:
            kwargs["proxy"] = self.proxy_config

        self.context = await self.playwright.chromium.launch_persistent_context(**kwargs)
        await self._apply_stealth_scripts()
        return self

    async def _apply_stealth_scripts(self) -> None:
        """Inject JavaScript patches into context to mask automation signals."""
        if not self.context:
            return
        await self.context.add_init_script("""
            // Mask webdriver flag
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Mask plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mask languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Mask chrome runtime
            window.chrome = { runtime: {} };

            // Mask permissions query
            if (window.navigator.permissions) {
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) =>
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters);
            }
        """)

    async def new_page(self) -> Page:
        if not self.context:
            raise RuntimeError("BrowserSession must be started before creating a page.")
        return await self.context.new_page()

    @property
    def pages(self) -> List[Page]:
        if not self.context:
            return []
        return self.context.pages

    async def close(self) -> None:
        """Close browser context and stop Patchright engine."""
        if self.context:
            try:
                await self.context.close()
            except Exception as e:
                logger.debug(f"Error closing browser context: {e}")
            self.context = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright engine: {e}")
            self.playwright = None
