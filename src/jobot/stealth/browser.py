import logging
from pathlib import Path
from typing import Any

from patchright.async_api import BrowserContext, Locator, Page, Playwright, async_playwright

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
        proxy_config: dict[str, Any] | None = None,
        session_dir: Path | None = None,
    ):
        self.portal = portal
        self.headless = headless
        self.proxy_config = proxy_config
        if session_dir is None:
            session_dir = Path.home() / ".jobot" / "sessions" / portal
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    async def start(self) -> "BrowserSession":
        """Launch Patchright persistent browser context with stealth parameters."""
        self.playwright = await async_playwright().start()

        kwargs: dict[str, Any] = {
            "user_data_dir": str(self.session_dir),
            "headless": self.headless,
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "Asia/Kolkata",
            "args": [
                "--disable-blink-features=AutomationControlled",
                # Audit fix JOB-SEC-012: removed ``--no-sandbox``. Disabling
                # the Chromium sandbox turns every renderer compromise into a
                # full-process compromise (the sandbox is the boundary that
                # limits a malicious page's blast radius). The previous
                # justification for ``--no-sandbox`` was Docker/container
                # compatibility (the sandbox needs a userns setup that some
                # minimal containers lack); the correct fix for that case is
                # to configure the container with ``--cap-add=SYS_ADMIN``
                # (or, better, ``--security-opt=syscd_always_seccomp``) so
                # the sandbox keeps working, rather than disabling it
                # globally. ``--disable-dev-shm-usage`` is kept because it
                # is a benign workaround for small ``/dev/shm`` in Docker
                # and does not weaken the security boundary.
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

    # ------------------------------------------------------------------
    # Page automation helpers (Phase 3, T3.6 — Easy Apply saga)
    # ------------------------------------------------------------------

    def _locator(self, selector: str, page: Page | None) -> Locator:
        target = page or (self.pages[0] if self.pages else None)
        if target is None:
            raise RuntimeError("No active page; call navigate() or new_page() first.")
        return target.locator(selector)

    async def navigate(self, url: str, page: Page | None = None) -> Page:
        """Open URL in a (new) page and wait for DOM content."""
        target = page or (self.pages[0] if self.pages else None)
        if target is None:
            target = await self.new_page()
        await target.goto(url, wait_until="domcontentloaded", timeout=60000)
        return target

    async def is_visible(
        self, selector: str, page: Page | None = None, timeout_ms: int = 3000
    ) -> bool:
        locator = self._locator(selector, page)
        try:
            await locator.first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def wait_for(
        self, selector: str, page: Page | None = None, timeout_ms: int = 15000
    ) -> None:
        """Wait until the first matching element is visible."""
        locator = self._locator(selector, page)
        await locator.first.wait_for(state="visible", timeout=timeout_ms)

    async def click(self, selector: str, page: Page | None = None) -> None:
        locator = self._locator(selector, page)
        await locator.first.wait_for(state="visible", timeout=15000)
        await locator.first.click()

    async def fill(self, selector: str, value: str, page: Page | None = None) -> None:
        locator = self._locator(selector, page)
        await locator.first.fill(str(value))

    async def type_slow(self, selector: str, value: str, page: Page | None = None) -> None:
        """Type with human-like keystroke delays (behavioral mimicry)."""
        locator = self._locator(selector, page)
        await locator.first.click()
        await locator.first.press_sequentially(str(value), delay=60)

    async def text_of(self, selector: str, page: Page | None = None) -> str:
        locator = self._locator(selector, page)
        return (await locator.first.inner_text()).strip()

    async def screenshot(self, path: Path, page: Page | None = None) -> Path:
        target = page or (self.pages[0] if self.pages else None)
        if target is None:
            raise RuntimeError("No active page to screenshot")
        path.parent.mkdir(parents=True, exist_ok=True)
        await target.screenshot(path=str(path))
        return path

    @property
    def pages(self) -> list[Page]:
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
