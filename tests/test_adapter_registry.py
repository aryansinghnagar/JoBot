from jobot.adapters import (
    AdapterRegistry,
    CutshortAdapter,
    FounditAdapter,
    GlassdoorAdapter,
    GreenhouseAdapter,
    HiristAdapter,
    IndeedAdapter,
    InstahyreAdapter,
    LeverAdapter,
    LinkedInAdapter,
    MockATSAdapter,
    NaukriAdapter,
    ShineAdapter,
    SmartRecruitersAdapter,
    WellfoundAdapter,
    WorkdayAdapter,
    ZipRecruiterAdapter,
)


def test_adapter_registry_mapping():
    expected_mappings = {
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

    for site_name, expected_cls in expected_mappings.items():
        adapter = AdapterRegistry.get_adapter(site_name)
        assert isinstance(adapter, expected_cls), f"Expected {expected_cls.__name__} for '{site_name}', got {type(adapter).__name__}"
