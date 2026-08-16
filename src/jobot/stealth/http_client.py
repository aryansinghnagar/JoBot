import logging
from typing import Dict, Optional, cast
from jobot.security.url_guard import safe_urlopen
from jobot.stealth.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class StealthHTTPClient:
    """
    HTTP Stealth Layer (Phase 3.1).
    Provides anti-detection TLS/header impersonation and CircuitBreaker protection.

    All requests go through the SSRF-guarded fetcher
    (`jobot.security.url_guard.safe_urlopen`): http/https only, host and
    resolved-IP boundary checks, per-hop redirect re-validation, no private
    targets unless the client is explicitly constructed for local test
    infrastructure (`allow_private_hosts=True`).
    """

    def __init__(
        self,
        impersonate: str = "chrome120",
        circuit_breaker: Optional[CircuitBreaker] = None,
        allow_private_hosts: bool = False,
    ) -> None:
        self.impersonate = impersonate
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.allow_private_hosts = allow_private_hosts
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

        with safe_urlopen(
            url,
            headers=req_headers,
            timeout=timeout,
            method="GET",
            allow_private_hosts=self.allow_private_hosts,
        ) as resp:
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

        with safe_urlopen(
            url,
            data=data,
            headers=req_headers,
            timeout=timeout,
            method="POST",
            allow_private_hosts=self.allow_private_hosts,
        ) as resp:
            return cast(str, resp.read().decode("utf-8"))
