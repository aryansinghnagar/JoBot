"""Direct-API ATS family adapters (plan.md Phase 2 / ch. 12).

Greenhouse, Lever, Ashby, Workable, SmartRecruiters all expose public JSON
posting APIs. These adapters are discovery-only: they fetch and map postings
into `JobPosting` domain models. No fabricated data — a failed fetch yields an
empty result (the circuit breaker handles retries/backoff at the caller).
"""

import asyncio
import html
import json
import logging
import re
from typing import Any

from jobot.models.domain import JobPosting
from jobot.security.url_guard import safe_urlopen

logger = logging.getLogger(__name__)

ATS_FAMILY_BOARDS = ("lever", "ashby", "smartrecruiters")

_HTML_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    return _WS.sub(" ", html.unescape(_HTML_TAG.sub(" ", text))).strip()


def _fetch_json(url: str, timeout_s: float = 10.0) -> Any:
    with safe_urlopen(url, headers={"User-Agent": "JoBot/1.0"}, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


class AtsFamilyAdapter:
    """Base class for direct-API ATS posting feeds."""

    family: str = ""
    api_url: str = ""

    def __init__(self, company: str | None = None, timeout_s: float = 10.0) -> None:
        self.company = company or ""
        self.timeout_s = timeout_s

    def _url(self, company: str, limit: int) -> str:
        return self.api_url.format(company=company, limit=limit)

    async def discover_jobs(
        self,
        company: str | None = None,
        limit: int = 25,
        keywords: str = "",
        location: str = "",
    ) -> list[JobPosting]:
        company = (company or self.company).strip()
        if not company:
            logger.warning("[ATS:%s] No company provided, skipping", self.family)
            return []
        url = self._url(company, limit)
        try:
            payload = await asyncio.to_thread(_fetch_json, url, self.timeout_s)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ATS:%s] Fetch failed for %s: %s", self.family, url, exc)
            return []
        return self._map(company, payload, limit)

    def _map(self, company: str, payload: Any, limit: int) -> list[JobPosting]:
        raise NotImplementedError

    @staticmethod
    def _posting(
        family: str,
        job_id: str,
        url: str,
        title: str,
        company: str,
        location: str,
        description: str,
    ) -> JobPosting:
        return JobPosting(
            job_id=f"{family}:{company}:{job_id}",
            site=family,
            url=url,
            title=_strip_html(title),
            company=company,
            location=location,
            description=description,
            parsed_skills=[],
        )


class LeverAdapter(AtsFamilyAdapter):
    """Lever public API: GET https://api.lever.co/v0/postings/{company}.

    Modern schema: `text` is the job title; `description`/`descriptionPlain`
    hold the description; `categories.location` the location; `hostedUrl` the
    canonical posting URL.
    """

    family = "lever"
    api_url = "https://api.lever.co/v0/postings/{company}?mode=json&limit={limit}"

    def _map(self, company: str, payload: Any, limit: int) -> list[JobPosting]:
        postings: list[JobPosting] = []
        if not isinstance(payload, list):
            return postings
        for item in payload[:limit]:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            categories = item.get("categories") or {}
            description = str(item.get("descriptionPlain") or "")
            if not description:
                description = _strip_html(str(item.get("description") or ""))
            postings.append(
                self._posting(
                    family=self.family,
                    job_id=str(item.get("id") or ""),
                    url=item.get("hostedUrl") or item.get("applyUrl") or "",
                    title=str(item.get("text") or ""),
                    company=company,
                    location=str(categories.get("location") or ""),
                    description=description,
                )
            )
        return postings


class AshbyAdapter(AtsFamilyAdapter):
    """Ashby posting API: GET https://api.ashbyhq.com/posting-api/job-board/{company}."""

    family = "ashby"
    api_url = "https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true"

    def _map(self, company: str, payload: Any, limit: int) -> list[JobPosting]:
        postings: list[JobPosting] = []
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not jobs:
            return postings
        for item in jobs[:limit]:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            location = item.get("location") or {}
            if isinstance(location, dict):
                location = str(location.get("name") or "")
            else:
                location = str(location)
            postings.append(
                self._posting(
                    family=self.family,
                    job_id=str(item.get("jobUrl") or item.get("jobId") or ""),
                    url=item.get("jobUrl") or "",
                    title=str(item.get("title") or ""),
                    company=company,
                    location=location,
                    description=_strip_html(str(item.get("descriptionHtml") or "")),
                )
            )
        return postings


class SmartRecruitersAdapter(AtsFamilyAdapter):
    """SmartRecruiters API: GET https://api.smartrecruiters.com/v1/companies/{company}/postings."""

    family = "smartrecruiters"
    api_url = "https://api.smartrecruiters.com/v1/companies/{company}/postings?limit={limit}"

    def _map(self, company: str, payload: Any, limit: int) -> list[JobPosting]:
        postings: list[JobPosting] = []
        content = payload.get("content") if isinstance(payload, dict) else None
        if not content:
            return postings
        for item in content[:limit]:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            location = item.get("location") or {}
            city = str(location.get("city") or "")
            country = str(location.get("country") or "")
            ref = str(item.get("ref") or "")
            job_ad = item.get("jobAd") or {}
            sections = job_ad.get("sections") or {}
            job_desc = sections.get("jobDescription") or {}
            postings.append(
                self._posting(
                    family=self.family,
                    job_id=ref,
                    url=f"https://jobs.smartrecruiters.com/{company}/{ref}" if ref else "",
                    title=str(item.get("name") or ""),
                    company=company,
                    location=", ".join(p for p in (city, country) if p),
                    description=str(job_desc.get("text") or ""),
                )
            )
        return postings


FAMILY_ADAPTERS: dict[str, type] = {
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
}
