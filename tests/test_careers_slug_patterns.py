"""Tests for CareerPageScanner slug regex extraction across diverse ATS URL variants (JOB-AUD-004)."""

from jobot.scrapers.careers import CareerPageScanner


def test_slug_patterns_with_underscores_and_dots():
    scanner = CareerPageScanner()

    # Greenhouse with dots/underscores
    html_gh = '<a href="https://boards.greenhouse.io/acme_corp.global/jobs/123">Apply</a>'
    family_gh = scanner.fingerprint(html_gh)
    assert family_gh == "greenhouse"
    slug_gh = scanner._extract_slug(html_gh, family_gh)
    assert slug_gh == "acme_corp.global"

    # Lever with underscores
    html_lever = '<a href="https://jobs.lever.co/stripe_payments/456">Stripe</a>'
    family_lever = scanner.fingerprint(html_lever)
    assert family_lever == "lever"
    slug_lever = scanner._extract_slug(html_lever, family_lever)
    assert slug_lever == "stripe_payments"

    # Ashby with hyphens and numbers
    html_ashby = '<a href="https://jobs.ashbyhq.com/openai-labs-2026/789">OpenAI</a>'
    family_ashby = scanner.fingerprint(html_ashby)
    assert family_ashby == "ashby"
    slug_ashby = scanner._extract_slug(html_ashby, family_ashby)
    assert slug_ashby == "openai-labs-2026"
