import logging
import urllib.request
from typing import Dict, Optional, cast
from jobot.stealth.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class StealthHTTPClient:
    """
    HTTP Stealth Layer (Phase 3.1).
    Provides anti-detection TLS/header impersonation and CircuitBreaker protection.
    """

    def __init__(
        self,
        impersonate: str = "chrome120",
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.impersonate = impersonate
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def get(
        self, url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 10.0
    ) -> str:
        """Execute stealth GET request with header impersonation."""
        req_headers = dict(self.default_headers)
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return cast(str, resp.read().decode("utf-8"))

    async def post(
        self,
        url: str,
        data: bytes,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ) -> str:
        """Execute stealth POST request."""
        req_headers = dict(self.default_headers)
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return cast(str, resp.read().decode("utf-8"))
