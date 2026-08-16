from typing import Any, Dict, cast
from urllib.parse import urlsplit

from jobot.adapters.base import SiteAdapter
from jobot.adapters.greenhouse import GreenhouseAdapter
from jobot.adapters.indeed import IndeedAdapter
from jobot.adapters.lever import LeverAdapter
from jobot.adapters.linkedin import LinkedInAdapter
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.adapters.more_adapters import (
    CutshortAdapter,
    FounditAdapter,
    GlassdoorAdapter,
    HiristAdapter,
    InstahyreAdapter,
    ShineAdapter,
    SmartRecruitersAdapter,
    WellfoundAdapter,
    ZipRecruiterAdapter,
)
from jobot.adapters.naukri import NaukriAdapter
from jobot.adapters.workday import WorkdayAdapter

# Canonical site -> hostname suffixes. A URL matches only when its parsed
# hostname IS the suffix or is a subdomain of it (exact/suffix match on the
# netloc, never substring matching against the raw URL — see CodeQL
# py/incomplete-url-substring-sanitization). Only sites with a registered
# adapter are listed; "ashby" intentionally absent (no adapter registered).
_SITE_HOST_SUFFIXES: Dict[str, tuple] = {
    "lever": ("lever.co",),
    "greenhouse": ("greenhouse.io",),
    "linkedin": ("linkedin.com",),
    "naukri": ("naukri.com",),
    "indeed": ("indeed.com",),
    "smartrecruiters": ("smartrecruiters.com",),
    "workday": ("myworkdayjobs.com",),
    "glassdoor": ("glassdoor.com",),
    "ziprecruiter": ("ziprecruiter.com",),
    "shine": ("shine.com",),
    "foundit": ("foundit.com", "foundit.in"),
    "hirist": ("hirist.tech",),
    "instahyre": ("instahyre.com",),
    "cutshort": ("cutshort.io",),
    "wellfound": ("wellfound.com",),
}


def _host_matches_suffix(host: str, suffix: str) -> bool:
    host = host.lower().rstrip(".")
    return host == suffix or host.endswith("." + suffix)


def infer_site(url: str) -> str:
    """Infer the site id from a job URL via exact host-suffix matching.

    Raises ValueError for unknown hosts instead of guessing a default (D1 in
    MASTER_PLAN_EXPANDED.md Section 8): a wrong adapter silently applied to a
    URL is worse than an explicit error. Scheme-less inputs that look like a
    bare host are retried once with an https:// prefix.
    """
    parsed = urlsplit(str(url).strip())
    if not parsed.netloc and "." in (parsed.path.split("/", 1)[0] or ""):
        parsed = urlsplit("https://" + str(url).strip())
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(
            f"Cannot infer job site from URL (no hostname): {url!r}. "
            f"Pass --site explicitly or use a supported site."
        )
    for site, suffixes in _SITE_HOST_SUFFIXES.items():
        if any(_host_matches_suffix(host, suffix) for suffix in suffixes):
            return site
    raise ValueError(
        f"Unknown job site host: {host!r}. Supported hosts: "
        + ", ".join(sorted({s for suffixes in _SITE_HOST_SUFFIXES.values() for s in suffixes}))
        + ". Run `jobot list-sites` for the full adapter list."
    )


class AdapterRegistry:
    """
    Unified SiteAdapter Registry (Layer 5).
    Maps site name to corresponding SiteAdapter implementation across discovery, runner, and CLI.
    """

    _registry: Dict[str, Any] = {
        "naukri": NaukriAdapter,
        "linkedin": LinkedInAdapter,
        "indeed": IndeedAdapter,
        "greenhouse": GreenhouseAdapter,
        "lever": LeverAdapter,
        "workday": WorkdayAdapter,
        "glassdoor": GlassdoorAdapter,
        "ziprecruiter": ZipRecruiterAdapter,
        "shine": ShineAdapter,
        "foundit": FounditAdapter,
        "hirist": HiristAdapter,
        "instahyre": InstahyreAdapter,
        "cutshort": CutshortAdapter,
        "wellfound": WellfoundAdapter,
        "smartrecruiters": SmartRecruitersAdapter,
        "mock_ats": MockATSAdapter,
    }

    @classmethod
    def get_adapter(cls, site: str) -> SiteAdapter:
        s = site.lower().strip()
        adapter_cls = cls._registry.get(s)
        if adapter_cls is None:
            raise ValueError(f"No adapter registered for portal: {site}")
        return cast(SiteAdapter, adapter_cls())

    @classmethod
    def list_supported_sites(cls) -> list[str]:
        return list(cls._registry.keys())


__all__ = ["AdapterRegistry", "infer_site"]
