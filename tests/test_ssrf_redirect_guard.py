"""Unit and integration tests for SSRF per-hop redirect verification (Phase 1)."""

import pytest

from jobot.security.url_guard import (
    SafeRedirectHandler,
    create_safe_httpx_client,
    validate_fetch_url,
    validate_redirect_url,
)


class TestRedirectSSRFGuard:
    def test_validate_redirect_url_passes_public_target(self):
        target = "https://boards-api.greenhouse.io/v1/boards/acme/jobs"
        assert validate_redirect_url(target) == target

    @pytest.mark.parametrize(
        "target",
        [
            "http://127.0.0.1:8080/admin",
            "http://localhost:5000/internal",
            "http://169.254.169.254/latest/meta-data",
            "http://10.0.0.1/secrets",
            "http://192.168.1.1/router",
            "http://[::1]/debug",
        ],
    )
    def test_validate_redirect_url_blocks_internal_targets(self, target):
        with pytest.raises(ValueError, match="SSRF guard"):
            validate_redirect_url(target)

    def test_safe_redirect_handler_blocks_malicious_redirect(self):
        handler = SafeRedirectHandler(allow_private_hosts=False)
        with pytest.raises(ValueError, match="SSRF guard"):
            handler.redirect_request(
                req=None,
                fp=None,
                code=302,
                msg="Found",
                headers={},
                newurl="http://127.0.0.1:8000/steal",
            )

    def test_safe_redirect_handler_allows_private_when_flagged(self):
        handler = SafeRedirectHandler(allow_private_hosts=True)
        url = "http://127.0.0.1:5800/jobs"
        assert handler.allow_private_hosts is True
        assert validate_fetch_url(url, allow_private_hosts=True) == url

    @pytest.mark.asyncio
    async def test_safe_httpx_client_creation(self):
        client = create_safe_httpx_client(allow_private_hosts=False, timeout=5.0)
        assert client is not None
        assert len(client.event_hooks.get("response", [])) > 0
        await client.aclose()
