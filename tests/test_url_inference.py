"""Adversarial URL-sanitization tests for infer_site() and Workday host matching.

Guards against the substring-matching class of URL confusion
(CodeQL py/incomplete-url-substring-sanitization): a host must match by
exact/suffix comparison of the parsed netloc, never by substring search over
the raw URL. Unknown hosts raise ValueError instead of falling back to a
default adapter (decision D1).
"""

import pytest
from jobot.adapters.registry import AdapterRegistry, infer_site
from jobot.adapters.workday import WorkdayApi

# --- Known-good URLs: exact host or subdomain ------------------------------

KNOWN_GOOD = [
    ("https://jobs.lever.co/acme/1234-5678", "lever"),
    ("https://lever.co/acme", "lever"),
    ("https://boards.greenhouse.io/acme/jobs/123", "greenhouse"),
    ("https://job-boards.greenhouse.io/acme", "greenhouse"),
    ("https://www.linkedin.com/jobs/view/123", "linkedin"),
    ("https://linkedin.com/jobs/collections/", "linkedin"),
    ("https://www.naukri.com/job-listings-123", "naukri"),
    ("https://indeed.com/viewjob?jk=abc", "indeed"),
    ("https://in.indeed.com/viewjob?jk=abc", "indeed"),
    ("https://jobs.smartrecruiters.com/Acme/123", "smartrecruiters"),
    ("https://careers.acme.wd1.myworkdayjobs.com/careers", "workday"),
    ("https://toptal.wd3.myworkdayjobs.com/wday/cxs/toptal/Toptal", "workday"),
    ("https://www.glassdoor.com/job-listing/software-engineer", "glassdoor"),
    ("https://www.ziprecruiter.com/jobs/j/abc", "ziprecruiter"),
    ("https://www.shine.com/job-search/", "shine"),
    ("https://www.foundit.in/seeker/job-details", "foundit"),
    ("https://www.hirist.tech/jobs/", "hirist"),
    ("https://www.instahyre.com/search-jobs/", "instahyre"),
    ("https://cutshort.io/jobs", "cutshort"),
    ("https://wellfound.com/jobs", "wellfound"),
    ("https://jobs.ashbyhq.com/acme/123", "ashby"),
    ("https://apply.workable.com/spotify/j/123", "workable"),
    ("https://hotjar.recruitee.com/o/123", "recruitee"),
    ("https://jobs.teamtailor.com/jobs/123", "teamtailor"),
    ("https://stripe.bamboohr.com/careers/123", "bamboohr"),
    # Scheme-less input that still looks like a host is retried with https://
    ("boards.greenhouse.io/acme/jobs/123", "greenhouse"),
    ("jobs.lever.co/acme/1234", "lever"),
    # Case-insensitive host, trailing dot, explicit port
    ("https://JOBS.LEVER.CO/acme/1", "lever"),
    ("https://jobs.lever.co./acme/1", "lever"),
    ("https://jobs.lever.co:443/acme/1", "lever"),
]


# --- Adversarial: substring lookalikes must NOT match -----------------------

ADVERSARIAL = [
    # lookalike domain that merely CONTAINS the suffix as a substring
    "https://notlever.co/jobs",
    "https://lever.co.evil.com/jobs",
    "https://evil-lever.co/jobs",
    "https://greenhouse.io.evil.com/jobs",
    "https://fakelinkedin.com/jobs",
    "https://linkedin.com.evil.at/jobs",
    "https://ashbyhq.com.evil.com/jobs",
    "https://evil-workable.com/jobs",
    "https://notrecruitee.com/jobs",
    "https://bamboohr.com.attacker.com/careers",
    # suffix smuggled in the path or query
    "https://evil.com/jobs?next=https://jobs.lever.co",
    "https://evil.com/redirect/https%3A%2F%2Fboards.greenhouse.io",
    "https://evil.com/myworkdayjobs.com",
    # userinfo credential confusion: hostname is evil.com
    "https://jobs.lever.co@evil.com/acme/1",
    "https://boards.greenhouse.io:leverage@evil.com/jobs/1",
    # homoglyph-ish / dot tricks
    "https://jobs.lever.co.evil.com.acme.dev/jobs",
    "https://myworkdayjobs.com.evil.io/careers",
    # unknown-but-plausible hosts
    "https://example.com/careers",
    "https://myworkdays.com/jobs",
    # not a URL at all
    "",
    "not a url",
    "https://",
    "http:///jobs",
]


@pytest.mark.parametrize("url,expected", KNOWN_GOOD)
def test_infer_site_known_good(url: str, expected: str) -> None:
    assert infer_site(url) == expected


@pytest.mark.parametrize("url", ADVERSARIAL)
def test_infer_site_adversarial_raises(url: str) -> None:
    with pytest.raises(ValueError):
        infer_site(url)


def test_infer_site_error_message_guides_user() -> None:
    with pytest.raises(ValueError) as excinfo:
        infer_site("https://example.com/careers")
    msg = str(excinfo.value)
    assert "example.com" in msg
    assert "list-sites" in msg


def test_every_inferred_site_has_registered_adapter() -> None:
    registered = set(AdapterRegistry.list_supported_sites())
    known_urls = [
        "https://jobs.lever.co/x",
        "https://boards.greenhouse.io/x",
        "https://www.linkedin.com/jobs/view/1",
        "https://www.naukri.com/x",
        "https://indeed.com/x",
        "https://jobs.smartrecruiters.com/x",
        "https://acme.wd1.myworkdayjobs.com/x",
        "https://www.glassdoor.com/x",
        "https://www.ziprecruiter.com/x",
        "https://www.shine.com/x",
        "https://www.foundit.in/x",
        "https://www.hirist.tech/x",
        "https://www.instahyre.com/x",
        "https://cutshort.io/x",
        "https://wellfound.com/x",
    ]
    for url in known_urls:
        site = infer_site(url)
        assert site in registered, f"{url} infers to unregistered site {site!r}"


# --- Workday _split_company host-suffix hardening ---------------------------


@pytest.mark.parametrize(
    ("spec", "expected_tenant"),
    [
        ("nvidia", "nvidia"),
        ("nvidia.wd1.myworkdayjobs.com", "nvidia"),
        ("https://toptal.wd3.myworkdayjobs.com/wday/cxs/toptal/Toptal", "toptal"),
    ],
)
def test_workday_split_company_valid(spec: str, expected_tenant: str) -> None:
    tenant, _site = WorkdayApi._split_company(spec)
    assert tenant == expected_tenant


@pytest.mark.parametrize(
    "spec",
    [
        # substring-smuggled host in a query must not be treated as a Workday
        # host. These fall through to the generic tenant heuristic and then
        # fail honestly at discovery time (bogus tenant -> empty cxs feed).
        "evil.com/?redirect=myworkdayjobs.com",
        "fake-myworkdayjobs.com",
    ],
)
def test_workday_split_company_adversarial(spec: str) -> None:
    tenant, _site = WorkdayApi._split_company(spec)
    # The Workday-host branch is unreachable for these specs: a tenant equal
    # to the smuggled host label would mean the branch matched.
    assert tenant != "myworkdayjobs", (
        f"adversarial spec {spec!r} was parsed as a Workday host tenant"
    )


def test_workday_split_company_lookalike_domain_is_generic() -> None:
    # Not URL-routed to Workday: parsed by the generic dotted-name heuristic,
    # so the bogus tenant never reaches a real careers host.
    tenant, _site = WorkdayApi._split_company("myworkdayjobs.com.evil.io")
    assert tenant == "myworkdayjobs"  # generic branch: parts[0] of the split
    with pytest.raises(ValueError):
        WorkdayApi._tenant_site_from_host("myworkdayjobs.com.evil.io")


def test_workday_split_company_non_workday_url_raises() -> None:
    # A URL whose host is not a Workday careers host must raise, not fabricate.
    with pytest.raises(ValueError):
        WorkdayApi._split_company("https://evil.com/myworkdayjobs.com")
