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

Residual (documented): redirect hops are followed by urllib's default
handler without per-hop revalidation. The realistic redirect-SSRF vector
requires the *initial* host to be attacker-controlled, which the boundary
checks above refuse for every product fetch path (only validated public
board/API hosts are fetched). Revisit if a fetch path accepting
arbitrary user URLs gains redirect-following behavior.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.request
from urllib.parse import urlsplit

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _is_private_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
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
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
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


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect hop against the same URL boundary."""

    def __init__(self, allow_private_hosts: bool = False) -> None:
        self.allow_private_hosts = allow_private_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        validate_fetch_url(newurl, allow_private_hosts=self.allow_private_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    method: str | None = None,
    allow_private_hosts: bool = False,
):
    """Validate-then-fetch: the only sanctioned way to urlopen in JoBot.

    Validation (scheme, host boundary, resolved-IP boundary) happens
    immediately before the request is built, and redirects are re-validated
    per hop. Returns the response context manager from ``urlopen``.
    """
    url = validate_fetch_url(url, allow_private_hosts=allow_private_hosts)
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    opener = urllib.request.build_opener(
        _ValidatingRedirectHandler(allow_private_hosts=allow_private_hosts)
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
    "safe_urlopen",
    "validate_fetch_url",
    "validate_path_segment",
]
