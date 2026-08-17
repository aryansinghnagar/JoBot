"""Regression test: no adapter may report SUBMITTED without a real network interaction.

This test imports every registered adapter and verifies that discovery-only
adapters raise AdapterCapabilityError (or NotImplementedError) on
submit_application(), and that no adapter fabricates confirmation IDs.

Part of Phase 1 P0 safety remediation.
"""

import pytest
from jobot.adapters.capabilities import AdapterCapability, AdapterCapabilityError
from jobot.adapters.registry import AdapterRegistry
from jobot.models.domain import Application


# Adapters that have real submission capability (API or browser).
# These are the ONLY adapters that should NOT raise on submit_application().
REAL_SUBMIT_SITES = frozenset({
    "greenhouse",   # Real HTTP POST to boards-api.greenhouse.io
    "lever",        # Real HTTP POST to api.lever.co
    "workday",      # Real browser submit via Patchright
    "linkedin",     # Real browser submit via EasyApplySaga
    "naukri",       # Real browser submit via Patchright
    "mock_ats",     # Test-only adapter for local Flask server
})


def _dummy_app(site: str) -> Application:
    return Application(
        application_id="test_guard_app_001",
        job_id="test_job_001",
        user_profile_id="test_profile",
        site=site,
        idempotency_key=f"guard_{site}_001",
    )


@pytest.mark.parametrize("site", sorted(
    set(AdapterRegistry.list_supported_sites()) - REAL_SUBMIT_SITES
))
@pytest.mark.asyncio
async def test_discovery_only_adapter_refuses_submit(site: str):
    """Discovery-only adapters must raise on submit_application()."""
    adapter = AdapterRegistry.get_adapter(site)
    app = _dummy_app(site)

    with pytest.raises((AdapterCapabilityError, NotImplementedError)):
        await adapter.submit_application(app)


@pytest.mark.parametrize("site", sorted(
    set(AdapterRegistry.list_supported_sites()) - REAL_SUBMIT_SITES
))
@pytest.mark.asyncio
async def test_discovery_only_adapter_refuses_verify(site: str):
    """Discovery-only adapters must raise on verify_submission()."""
    adapter = AdapterRegistry.get_adapter(site)
    app = _dummy_app(site)

    with pytest.raises((AdapterCapabilityError, NotImplementedError)):
        await adapter.verify_submission(app)


@pytest.mark.parametrize("site", sorted(
    set(AdapterRegistry.list_supported_sites()) - REAL_SUBMIT_SITES
))
def test_discovery_only_adapter_declares_no_submit_capability(site: str):
    """Discovery-only adapters must NOT have SUBMIT_API or SUBMIT_BROWSER capability."""
    adapter = AdapterRegistry.get_adapter(site)
    has_submit = bool(
        adapter.capabilities & (AdapterCapability.SUBMIT_API | AdapterCapability.SUBMIT_BROWSER)
    )
    assert not has_submit, (
        f"{site} adapter declares submit capability but is expected to be discovery-only"
    )


@pytest.mark.parametrize("site", sorted(REAL_SUBMIT_SITES - {"mock_ats"}))
def test_real_adapter_declares_submit_capability(site: str):
    """Real submission adapters must declare SUBMIT_API or SUBMIT_BROWSER capability."""
    adapter = AdapterRegistry.get_adapter(site)
    has_submit = bool(
        adapter.capabilities & (AdapterCapability.SUBMIT_API | AdapterCapability.SUBMIT_BROWSER)
    )
    assert has_submit, (
        f"{site} adapter is expected to have submit capability but declares: {adapter.capabilities}"
    )


def test_registry_can_submit_helper():
    """AdapterRegistry.can_submit() accurately reports real vs discovery-only."""
    for site in REAL_SUBMIT_SITES:
        assert AdapterRegistry.can_submit(site), f"Expected can_submit('{site}') == True"

    discovery_only = set(AdapterRegistry.list_supported_sites()) - REAL_SUBMIT_SITES
    for site in discovery_only:
        assert not AdapterRegistry.can_submit(site), f"Expected can_submit('{site}') == False"
