from typing import Any, Dict, cast
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


def infer_site(url: str) -> str:
    """Best-effort site inference from a job URL (shared by CLI and GUI sidecar)."""
    lowered = url.lower()
    if "lever.co" in lowered:
        return "lever"
    if "greenhouse.io" in lowered or "boards.greenhouse.io" in lowered:
        return "greenhouse"
    if "linkedin.com" in lowered:
        return "linkedin"
    if "naukri.com" in lowered:
        return "naukri"
    if "indeed.com" in lowered:
        return "indeed"
    if "jobs.ashbyhq.com" in lowered:
        return "ashby"
    if "smartrecruiters.com" in lowered:
        return "smartrecruiters"
    if "myworkdayjobs.com" in lowered:
        return "workday"
    return "greenhouse"


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
