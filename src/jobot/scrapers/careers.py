"""CareerPageScanner (plan.md Phase 2).

Fetches a company's careers page, fingerprints the ATS vendor from known
markers, and dispatches to the matching direct-API family adapter. Unknown
ATS vendors yield an empty result — never fabricated postings.

Config: `src/jobot/scrapers/career_sites.yaml` (schema + verified starter set).
"""

import asyncio
import logging
import re
from pathlib import Path
from re import Pattern
from typing import Any, cast

import yaml

from jobot.models.domain import JobPosting
from jobot.scrapers.ats import FAMILY_ADAPTERS, AtsFamilyAdapter
from jobot.security.url_guard import safe_urlopen

logger = logging.getLogger(__name__)

CAREER_SITES_YAML = Path(__file__).parent / "career_sites.yaml"

MARKER_PATTERNS: dict[str, Pattern[str]] = {
    "greenhouse": re.compile(r"boards\.greenhouse\.io"),
    "lever": re.compile(r"jobs\.lever\.co"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com"),
    "workable": re.compile(r"apply\.workable\.com"),
    "smartrecruiters": re.compile(r"smartrecruiters\.com"),
}

SLUG_PATTERNS: dict[str, Pattern[str]] = {
    "greenhouse": re.compile(r"boards\.greenhouse\.io/([A-Za-z0-9\-]+)"),
    "lever": re.compile(r"jobs\.lever\.co/([A-Za-z0-9\-]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9\-]+)"),
    "workable": re.compile(r"apply\.workable\.com/([A-Za-z0-9\-]+)"),
    "smartrecruiters": re.compile(r"smartrecruiters\.com/([A-Za-z0-9\-]+)"),
}


def _fetch_html(url: str, timeout_s: float = 10.0) -> str | None:
    try:
        with safe_urlopen(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JoBot/1.0"},
            timeout=timeout_s,
        ) as resp:
            return cast(str, resp.read().decode("utf-8", "replace"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[CareerPageScanner] fetch failed for %s: %s", url, exc)
        return None


class CareerPageScanner:
    """Fingerprint company career pages and scrape via the matching ATS API."""

    def __init__(
        self,
        config_path: Path | None = None,
        timeout_s: float = 10.0,
        companies: list[str] | None = None,
    ) -> None:
        self.config_path = config_path or CAREER_SITES_YAML
        self.timeout_s = timeout_s
        self.companies_override = companies or []
        self._config: dict[str, Any] = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        try:
            raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CareerPageScanner] cannot load %s: %s", self.config_path, exc)
            raw = {}
        if not isinstance(raw, dict):
            return {}
        return cast(dict[str, Any], raw)

    @property
    def companies(self) -> list[str]:
        if self.companies_override:
            return self.companies_override
        return [str(c) for c in self._config.get("companies", [])]

    def fingerprint(self, html_text: str) -> str | None:
        for family, pattern in MARKER_PATTERNS.items():
            if pattern.search(html_text):
                return family
        return None

    def _extract_slug(self, html_text: str, family: str) -> str | None:
        pattern = SLUG_PATTERNS.get(family)
        if pattern:
            match = pattern.search(html_text)
            if match:
                return match.group(1)
        return None

    def _family_adapter(self, family: str, company: str) -> AtsFamilyAdapter | None:
        if family == "greenhouse":
            from jobot.adapters.greenhouse import GreenhouseAdapter

            return cast(AtsFamilyAdapter, GreenhouseAdapter())
        if family == "workable":
            logger.info(
                "[CareerPageScanner] %s uses Workable; its public API requires per-account "
                "keys, skipping (no anonymous feed)",
                company,
            )
            return None
        adapter_cls = FAMILY_ADAPTERS.get(family)
        if adapter_cls is None:
            return None
        return cast(AtsFamilyAdapter, adapter_cls(company=company))

    async def scan_company(self, company: str, limit: int = 25) -> list[JobPosting]:
        """Fetch <company>.com/careers, fingerprint, and scrape via the ATS API."""
        company = company.strip().lower()
        if not company:
            return []
        careers_url = f"https://{company}.com/careers"
        html_text = await asyncio.to_thread(_fetch_html, careers_url, self.timeout_s)
        if not html_text:
            logger.warning("[CareerPageScanner] no HTML for %s", careers_url)
            return []
        family = self.fingerprint(html_text)
        if family is None:
            logger.info("[CareerPageScanner] no known ATS marker on %s", careers_url)
            return []
        slug = self._extract_slug(html_text, family) or company
        adapter = self._family_adapter(family, company=slug)
        if adapter is None:
            return []
        return await adapter.discover_jobs(company=slug, limit=limit)

    async def scan(self, companies: list[str], limit: int = 25) -> list[JobPosting]:
        postings: list[JobPosting] = []
        for company in companies:
            postings.extend(await self.scan_company(company, limit=limit))
        return postings

    async def discover_jobs(
        self,
        keywords: str = "",
        location: str = "",
        limit: int = 25,
        company: str | None = None,
    ) -> list[JobPosting]:
        """Uniform scraper interface: scan the configured/override company list."""
        targets = [company] if company else self.companies
        if not targets:
            logger.info("[CareerPageScanner] no companies configured; skipping")
            return []
        return await self.scan(targets, limit=limit)
