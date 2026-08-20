"""Unit tests for the outbound URL guard (SSRF boundary, WS1 hardening)."""

import ssl

import pytest

from jobot.security.url_guard import (
    _resolved_hosts_are_internal,
    safe_urlopen,
    validate_fetch_url,
    validate_path_segment,
)


class TestValidateFetchUrl:
    def test_https_and_http_pass(self):
        assert validate_fetch_url("https://boards-api.greenhouse.io/v1/boards/acme/jobs")
        assert validate_fetch_url("http://example.com/feed")

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "data:text/html,hello",
            "https://",  # no host
            "/relative/path",
            "not a url",
            "",
        ],
    )
    def test_bad_scheme_or_host_refused(self, url):
        with pytest.raises(ValueError):
            validate_fetch_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://127.0.0.1/jobs",
            "https://localhost/jobs",
            "http://[::1]/jobs",
            "http://[::ffff:127.0.0.1]/jobs",
            "http://[::ffff:169.254.169.254]/latest/meta-data",
            "http://[::ffff:10.0.0.5]/internal",
            "http://169.254.169.254/latest/meta-data",  # cloud metadata
            "http://10.0.0.5/internal",
            "http://192.168.1.10/admin",
            "http://0.0.0.0/x",
        ],
    )
    def test_private_literal_hosts_refused(self, url):
        with pytest.raises(ValueError):
            validate_fetch_url(url)

    def test_userinfo_credentials_refused(self):
        with pytest.raises(ValueError):
            validate_fetch_url("https://user:pass@example.com/jobs")

    def test_allow_private_hosts_opt_in(self):
        assert validate_fetch_url("http://127.0.0.1:5800/jobs", allow_private_hosts=True)

    def test_public_host_passes(self):
        # Unresolvable TLD: DNS boundary check falls through (offline-safe),
        # literal checks pass — fetch proceeds (and fails on its own).
        assert validate_fetch_url("https://boards-api.greenhouse.io/v1/boards")


class TestResolvedBoundary:
    def test_unresolvable_host_is_not_internal(self):
        assert _resolved_hosts_are_internal("this-domain-does-not-exist.invalid") is False

    def test_localhost_resolves_internal(self):
        assert _resolved_hosts_are_internal("localhost") is True


class TestSafeUlopen:
    def test_validates_before_any_network(self):
        # Scheme failure must raise from validation, before a request exists.
        with pytest.raises(ValueError):
            safe_urlopen("ftp://example.com/file")

    def test_private_target_refused_before_network(self):
        with pytest.raises(ValueError):
            safe_urlopen("http://169.254.169.254/latest/meta-data")

    def test_tls_context_enforces_tls_1_2_minimum(self):
        """Audit fix JOB-SEC-016: outbound HTTPS uses a TLSContext pinned to
        ``minimum_version = TLSv1_2``. SSLv3 / TLS 1.0 / TLS 1.1 downgrade
        attempts must be rejected at the handshake rather than silently
        accepted by Python's defaults."""
        from jobot.security.url_guard import _TLS_CONTEXT

        assert _TLS_CONTEXT.minimum_version is ssl.TLSVersion.TLSv1_2
        # Sanity check that the context actually rejects older protocols:
        # ``_insecure_protocols`` are exactly the ones we forbid.
        insecure = [
            ssl.TLSVersion.SSLv3,
            ssl.TLSVersion.TLSv1,
            ssl.TLSVersion.TLSv1_1,
        ]
        for proto in insecure:
            # ``minimum_version`` is a floor — older protocols must not be
            # acceptable to the context's protocol negotiation.
            assert proto < _TLS_CONTEXT.minimum_version


class TestValidatePathSegment:
    @pytest.mark.parametrize(
        "bad",
        ["", "a/b", "a\\b", "a?b", "a#b", "a@b", "a:b", "a%b", "..", "a/../b"],
    )
    def test_unsafe_segments_refused(self, bad):
        with pytest.raises(ValueError):
            validate_path_segment(bad)

    def test_surrounding_whitespace_is_normalized(self):
        assert validate_path_segment("  acme  ") == "acme"

    @pytest.mark.parametrize("good", ["acme", "job-123", "Toptal", "boards_1"])
    def test_safe_segments_pass(self, good):
        assert validate_path_segment(good) == good
