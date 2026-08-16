from typing import Dict, Type
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


class AdapterRegistry:
    """
    Unified SiteAdapter Registry (Layer 5).
    Maps site name to corresponding SiteAdapter implementation across discovery, runner, and CLI.
    """

    _registry: Dict[str, Type[SiteAdapter]] = {
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
            return NaukriAdapter()
        return adapter_cls()
