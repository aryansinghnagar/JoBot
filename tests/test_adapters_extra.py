import pytest
from jobot.adapters.base import SiteAdapter
from jobot.adapters.mock_ats import MockATSAdapter
from jobot.adapters.registry import AdapterRegistry
from jobot.models.domain import JobPosting


def test_site_adapters_inherit_base_class():
    registry = AdapterRegistry()
    supported_sites = registry.list_supported_sites()

    assert len(supported_sites) >= 16
    for site in supported_sites:
        adapter = registry.get_adapter(site)
        assert isinstance(adapter, SiteAdapter)
        assert hasattr(adapter, "site_name")
        assert hasattr(adapter, "parse_job_posting")
        assert hasattr(adapter, "fill_form")
        assert hasattr(adapter, "submit_application")
        assert hasattr(adapter, "verify_submission")


@pytest.mark.asyncio
async def test_mock_ats_adapter_contract():
    adapter = MockATSAdapter(base_url="http://127.0.0.1:5800")
    assert isinstance(adapter, SiteAdapter)
    assert adapter.site_name == "mock_ats"

    job = await adapter.parse_job_posting("http://127.0.0.1:5800/jobs/1")
    assert isinstance(job, JobPosting)
    assert job.site == "mock_ats"
    assert job.title != ""
    assert job.company != ""
    assert job.url != ""
