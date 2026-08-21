"""Outbound URL guard — single choke point for every URL the agent fetches.

JoBot fetches URLs that originate from user input, job boards, and plugin
data; every outbound HTTP surface must go through this module. Protections:

- http/https scheme only (no file:, ftp:, data: exfiltration channels)
- a non-empty hostname; no userinfo credentials in the URL
- private/loopback/link-local/reserved IP-literal hosts and ``localhost``
  are refused (SSRF boundary) unless the caller explicitly opts in for
  local test infrastructure (``allow_private_hosts=True``)
- best-effort DNS resolution: every resolved address is checked against
  the same private-range boundary (blocks hostnames that point inward);
  resolution failure falls through to the literal checks so offline
  hermetic tests are unaffected

- per-hop redirect re-validation: every redirect hop (301, 302, 303, 307, 308)
  is intercepted and re-validated against the SSRF boundary via ``SafeRedirectHandler``
  (urllib) and ``create_safe_httpx_client`` (httpx).
- TLS 1.2+ minimum protocol version enforced across all outbound TLS contexts.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
import urllib.request
from typing import Any
from urllib.parse import urlsplit

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return _is_private_ip(ip.ipv4_mapped)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_private_host(host: str) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return _is_private_ip(ip)


def _resolved_hosts_are_internal(host: str) -> bool:
    """Boundary check on DNS answers: True if ANY resolved address is
    loopback, link-local (covers the 169.254.169.254 cloud-metadata
    service), unspecified, or multicast — the SSRF crown jewels.

    Deliberately narrower than the literal-IP check: RFC1918-private and
    NAT64/DNS64 answers (``64:ff9b::/96``, which CPython classifies as
    private) are NOT refused, because corporate VPN and DNS64 transition
    networks legitimately resolve ordinary public sites into those ranges
    and refusing them would break every fetch on such hosts. Literal
    private IPs in the URL itself remain refused absolutely by
    ``_is_private_host``.

    Resolution failure (offline hermetic environments) returns False —
    the subsequent fetch will surface its own network error. Rebinding
    TOCTOU is documented as out of scope for the stdlib fetch layer.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError):
        return False
    for info in infos:
        addr = str(info[4][0])
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            return True
    return False


def validate_fetch_url(url: str, *, allow_private_hosts: bool = False) -> str:
    """Validate an outbound fetch URL; return it unchanged or raise ValueError.

    ``allow_private_hosts`` exists for local test infrastructure (the mock ATS
    server) that is loopback by design. Product code paths never set it.
    """
    url = str(url).strip()
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Refusing to fetch non-http(s) URL: {url!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"Refusing to fetch URL without a hostname: {url!r}")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"Refusing to fetch URL with embedded credentials: {url!r}")
    if not allow_private_hosts:
        if _is_private_host(host):
            raise ValueError(
                f"Refusing to fetch private/loopback host {host!r} (SSRF guard): {url!r}"
            )
        if _resolved_hosts_are_internal(host):
            raise ValueError(
                f"Refusing to fetch host {host!r}: resolves to a loopback/"
                f"link-local address (SSRF guard): {url!r}"
            )
    return url


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop against the SSRF URL boundary.

    Subclasses urllib's standard redirect handler so any 301, 302, 303, 307,
    or 308 redirect must pass ``validate_fetch_url`` before the subsequent hop
    is requested.
    """

    def __init__(self, allow_private_hosts: bool = False, max_redirects: int = 5) -> None:
        self.allow_private_hosts = allow_private_hosts
        self.max_redirects = max_redirects

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        validate_fetch_url(newurl, allow_private_hosts=self.allow_private_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Alias for backward compatibility
_ValidatingRedirectHandler = SafeRedirectHandler


# Audit fix JOB-SEC-016: enforce TLS 1.2+ on every outbound HTTPS fetch.
# Python's default ``ssl.create_default_context()`` already prefers TLS 1.2+
# but it does not *forbid* older protocols — a server that negotiates SSLv3 or
# TLS 1.0/1.1 would still be accepted. We construct a context with
# ``minimum_version = ssl.TLSVersion.TLSv1_2`` so any downgrade attempt is
# rejected at the TLS handshake. The context is module-level so it is created
# once per process and reused across fetches.
_TLS_CONTEXT: ssl.SSLContext = ssl.create_default_context()
_TLS_CONTEXT.minimum_version = ssl.TLSVersion.TLSv1_2


def validate_redirect_url(
    target_url: str,
    *,
    allow_private_hosts: bool = False,
) -> str:
    """Validate a redirect target URL extracted from a Location header or response.

    Raises ValueError if the target violates the SSRF boundary (private/loopback host).
    """
    return validate_fetch_url(target_url, allow_private_hosts=allow_private_hosts)


def create_safe_httpx_client(
    *,
    allow_private_hosts: bool = False,
    timeout: float = 60.0,
    max_connections: int = 100,
    max_keepalive_connections: int = 20,
    keepalive_expiry: float = 30.0,
) -> Any:
    """Factory creating an ``httpx.AsyncClient`` guarded against SSRF and TLS downgrade.

    Configured with:
    - Per-hop redirect inspection hook enforcing ``validate_fetch_url``;
    - Strict TLS 1.2+ minimum context;
    - Bounded connection pooling and keep-alive limits.
    """
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx is not installed — install with `pip install httpx>=0.27.0`")

    async def _check_redirect(response: httpx.Response) -> None:
        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if location:
                # Resolve relative redirects against the request URL
                target = str(response.url.join(location))
                validate_fetch_url(target, allow_private_hosts=allow_private_hosts)

    return httpx.AsyncClient(
        verify=_TLS_CONTEXT,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
        ),
        timeout=httpx.Timeout(timeout, connect=10.0),
        follow_redirects=True,
        event_hooks={"response": [_check_redirect]},
    )


def safe_urlopen(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    method: str | None = None,
    allow_private_hosts: bool = False,
) -> Any:
    """Validate-then-fetch: the only sanctioned way to urlopen in JoBot.

    Validation (scheme, host boundary, resolved-IP boundary) happens
    immediately before the request is built, and redirects are re-validated
    per hop by ``SafeRedirectHandler``. Outbound HTTPS calls use a module-level
    ``SSLContext`` pinned to ``minimum_version = TLSv1_2`` (audit fix JOB-SEC-016)
    so protocol downgrade attacks are rejected at the TLS handshake.
    Returns the response context manager from ``urlopen``.
    """
    url = validate_fetch_url(url, allow_private_hosts=allow_private_hosts)
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)  # noqa: S310
    opener = urllib.request.build_opener(
        SafeRedirectHandler(allow_private_hosts=allow_private_hosts),
        urllib.request.HTTPSHandler(context=_TLS_CONTEXT),
    )
    return opener.open(req, timeout=timeout)


def validate_path_segment(segment: str) -> str:
    """Validate a value that will be interpolated into a URL path component.

    Blocks path traversal, host confusion via '/', '\\', '@', ':', and friends.
    Suitable for board slugs, job ids, tenant names interpolated into
    API paths.
    """
    segment = str(segment).strip()
    if not segment or any(c in segment for c in "/\\?#@:%"):
        raise ValueError(f"Unsafe URL path segment: {segment!r}")
    if ".." in segment:
        raise ValueError(f"Unsafe URL path segment: {segment!r}")
    return segment


__all__ = [
    "SafeRedirectHandler",
    "_TLS_CONTEXT",
    "create_safe_httpx_client",
    "safe_urlopen",
    "validate_fetch_url",
    "validate_path_segment",
    "validate_redirect_url",
]
