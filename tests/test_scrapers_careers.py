"""CareerPageScanner tests: fingerprinting, slug extraction, dispatch, YAML config."""

from pathlib import Path

import pytest

from jobot.scrapers.careers import CareerPageScanner

GREENHOUSE_HTML = (
    '<html><a href="https://boards.greenhouse.io/acme">Careers</a>'
    '<script src="https://boards.greenhouse.io/acme"></script></html>'
)
LEVER_HTML = '<a href="https://jobs.lever.co/beta/123">Apply</a>'
ASHBY_HTML = '<a href="https://jobs.ashbyhq.com/gamma/456">Apply</a>'
WORKABLE_HTML = '<a href="https://apply.workable.com/delta/">Apply</a>'
NO_MARKER_HTML = "<html><body>We hire with a custom ATS.</body></html>"

YAML_SAMPLE = """\
schema_version: 1
ats_families:
  greenhouse:
    markers: ["boards.greenhouse.io"]
    slug_pattern: "boards.greenhouse.io/([A-Za-z0-9-]+)"
    api:
      base: "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
  ashby:
    markers: ["jobs.ashbyhq.com"]
    slug_pattern: "jobs.ashbyhq.com/([A-Za-z0-9-]+)"
    api:
      base: "https://api.ashbyhq.com/posting-api/job-board/{company}"
  workable:
    markers: ["apply.workable.com"]
    slug_pattern: "apply.workable.com/([A-Za-z0-9-]+)"
    api: null
    note: "Workable's public API requires per-account keys; no anonymous feed."
companies:
  - webflow
  - figma
"""


@pytest.fixture
def scanner(tmp_path: Path) -> CareerPageScanner:
    config = tmp_path / "career_sites.yaml"
    config.write_text(YAML_SAMPLE, encoding="utf-8")
    return CareerPageScanner(config_path=config)


def test_yaml_loaded(scanner: CareerPageScanner):
    assert scanner.companies == ["webflow", "figma"]
    assert scanner._config["schema_version"] == 1
    assert scanner._config["ats_families"]["workable"]["api"] is None


def test_companies_override(scanner: CareerPageScanner):
    scanner.companies_override = ["customco"]
    assert scanner.companies == ["customco"]


def test_empty_override_falls_back_to_yaml(scanner: CareerPageScanner):
    scanner.companies_override = []
    assert scanner.companies == ["webflow", "figma"]


def test_fingerprint_detects_families(scanner: CareerPageScanner):
    assert scanner.fingerprint(GREENHOUSE_HTML) == "greenhouse"
    assert scanner.fingerprint(LEVER_HTML) == "lever"
    assert scanner.fingerprint(ASHBY_HTML) == "ashby"
    assert scanner.fingerprint(WORKABLE_HTML) == "workable"


def test_fingerprint_unknown_returns_none(scanner: CareerPageScanner):
    assert scanner.fingerprint(NO_MARKER_HTML) is None
    assert scanner.fingerprint("") is None


def test_extract_slug(scanner: CareerPageScanner):
    assert scanner._extract_slug(GREENHOUSE_HTML, "greenhouse") == "acme"
    assert scanner._extract_slug(LEVER_HTML, "lever") == "beta"
    assert scanner._extract_slug(ASHBY_HTML, "ashby") == "gamma"
    assert scanner._extract_slug(WORKABLE_HTML, "workable") == "delta"


def test_family_adapter_greenhouse_returns_adapter(scanner: CareerPageScanner):
    adapter = scanner._family_adapter("greenhouse", "acme")
    assert adapter is not None
    assert type(adapter).__name__ == "GreenhouseAdapter"


def test_family_adapter_workable_is_skipped(scanner: CareerPageScanner):
    assert scanner._family_adapter("workable", "delta") is None


def test_family_adapter_known_families(scanner: CareerPageScanner):
    for family, expected in (("lever", "lever"), ("ashby", "ashby")):
        adapter = scanner._family_adapter(family, "acme")
        assert adapter is not None
        assert adapter.family == expected


def test_family_adapter_unknown_returns_none(scanner: CareerPageScanner):
    assert scanner._family_adapter("mystery_ats", "acme") is None


@pytest.mark.asyncio
async def test_discover_jobs_without_companies_is_empty(scanner: CareerPageScanner):
    scanner.companies_override = ["__no_such_company__"]
    assert await scanner.discover_jobs(limit=5) == []


@pytest.mark.asyncio
async def test_scan_company_fetch_failure_empty(scanner: CareerPageScanner, monkeypatch):
    def no_html(url: str, timeout_s: float = 10.0):
        return None

    monkeypatch.setattr("jobot.scrapers.careers._fetch_html", no_html)
    assert await scanner.scan_company("missingco") == []


@pytest.mark.asyncio
async def test_scan_company_unknown_family_empty(scanner: CareerPageScanner, monkeypatch):
    def html(url: str, timeout_s: float = 10.0):
        return NO_MARKER_HTML

    monkeypatch.setattr("jobot.scrapers.careers._fetch_html", html)
    assert await scanner.scan_company("customco") == []
