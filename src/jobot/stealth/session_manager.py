"""Browser Session Manager & Connection Pool (UC-09).

Manages persistent browser contexts, warm connection reuse, and lifecycle
cleanup across different ATS platforms and job boards.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict

from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)


class BrowserSessionPool:
    """Connection pool for BrowserSession instances."""

    def __init__(self, max_idle_sessions: int = 4) -> None:
        self.max_idle_sessions = max_idle_sessions
        self._pool: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(
        self, portal: str = "default", headless: bool = True
    ) -> AsyncIterator[BrowserSession]:
        """Acquire a BrowserSession from the pool or create a new one."""
        async with self._lock:
            session = self._pool.get(portal)
            if session is None or session.context is None:
                session = BrowserSession(portal=portal, headless=headless)
                await session.start()
                self._pool[portal] = session

        try:
            yield session
        except Exception as exc:
            logger.warning("Error during browser session on portal %s: %s", portal, exc)
            raise

    async def close_session(self, portal: str) -> None:
        """Close and remove a specific portal session."""
        async with self._lock:
            session = self._pool.pop(portal, None)
            if session:
                await session.close()

    async def close_all(self) -> None:
        """Close all pooled browser sessions cleanly."""
        async with self._lock:
            for portal, session in list(self._pool.items()):
                try:
                    await session.close()
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Error closing session for %s: %s", portal, exc)
            self._pool.clear()


__all__ = ["BrowserSessionPool"]
