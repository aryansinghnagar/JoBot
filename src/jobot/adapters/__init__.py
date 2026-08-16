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

__all__ = [
    "SiteAdapter",
    "MockATSAdapter",
    "NaukriAdapter",
    "LinkedInAdapter",
    "IndeedAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "WorkdayAdapter",
    "GlassdoorAdapter",
    "ZipRecruiterAdapter",
    "ShineAdapter",
    "FounditAdapter",
    "HiristAdapter",
    "InstahyreAdapter",
    "CutshortAdapter",
    "WellfoundAdapter",
    "SmartRecruitersAdapter",
]
