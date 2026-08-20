"""Workday ATS Adapter — honest discovery/parse + live-browser submit/verify.

Fabrication removed: this adapter never invents postings, form values, or
confirmation IDs. Discovery and parsing use Workday's public cxs JSON API
(unauthenticated tenant feed). Submit/verify drive a real Patchright browser
session and are refused honestly when live browser runs are disabled
(JOBOT_RUN_LIVE_BROWSER=1).
"""

import html
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any, cast

from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.security.url_guard import safe_urlopen
from jobot.stealth.browser import BrowserSession

logger = logging.getLogger(__name__)

WORKDAY_HOST_RE = re.compile(r"^(?P<tenant>[a-z0-9-]+)\.wd[0-9]*\.myworkdayjobs\.com$")

APPLY_BUTTON_SELECTORS = [
    "button[data-automation-id='applyButton']",
    "button[data-automation-id='bottomButtonRegion'] button",
    "button:has-text('Apply')",
    "a[data-automation-id='applyButton']",
]

SUBMIT_BUTTON_SELECTORS = [
    "button[data-automation-id='submitButton']",
    "button[data-automation-id='bottomButtonRegion'] button:has-text('Submit')",
    "button:has-text('Submit Application')",
]

CONFIRMATION_MARKERS = [
    "your application has been submitted",
    "application submitted",
    "you have applied",
    "thank you for applying",
    "application received",
]

ALREADY_APPLIED_MARKERS = [
    "you have already applied",
    "already applied",
    "you've already applied",
]

LOGIN_WALL_SELECTORS = [
    "input[name='emailAddress']",
    "input[data-automation-id='emailAddress']",
    "input[type='email']",
    "button:has-text('Sign In')",
]

GUEST_CONTINUE_SELECTORS = [
    "button:has-text('Continue as guest')",
    "button:has-text('Apply as guest')",
    "a:has-text('Continue as guest')",
]


def _now() -> datetime:
    return datetime.now(UTC)


class WorkdayApi:
    """Client for the public Workday cxs JSON API (no auth required)."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    @staticmethod
    def _split_company(company: str) -> tuple[str, str]:
        """Normalize a company spec to (tenant, site)."""
        company = company.strip().strip("/")
        if not company:
            raise ValueError("Workday discovery requires a company/tenant name.")
        lowered = company.lower()
        if lowered.startswith("http"):
            tenant, site = WorkdayApi._tenant_site_from_url(company)
            return tenant, site
        # Host-suffix match on the parsed netloc (never substring against the
        # raw spec: "evil.com/?x=myworkdayjobs.com" is not a Workday host).
        if "." in company:
            raw_host = urllib.parse.urlparse("https://" + company).netloc
            host = raw_host.split("@")[-1].split(":")[0].lower()
            if host == "myworkdayjobs.com" or host.endswith(".myworkdayjobs.com"):
                tenant, _ = WorkdayApi._tenant_site_from_host(host)
                return tenant, tenant
        parts = company.split(".")
        if len(parts) >= 2:
            return parts[0], parts[1]
        return parts[0], parts[0]

    @staticmethod
    def _tenant_site_from_host(host: str) -> tuple[str, str]:
        m = WORKDAY_HOST_RE.match(host)
        if not m:
            raise ValueError(f"Not a Workday careers host: {host}")
        return m.group("tenant"), m.group("tenant")

    @classmethod
    def _tenant_site_from_url(cls, url: str) -> tuple[str, str]:
        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Not a valid Workday URL: {url}")
        tenant, _ = cls._tenant_site_from_host(parsed.netloc)
        site = tenant
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[1] != "job" and parts[1] != "jobs":
            site = parts[1]
        return tenant, site

    @staticmethod
    def _job_id_from_url(url: str) -> str | None:
        parts = [p for p in url.rstrip("/").split("/") if p]
        if not parts:
            return None
        return urllib.parse.unquote(parts[-1])

    @staticmethod
    def _cxs_base(tenant: str, site: str) -> str:
        return f"https://{tenant}.wd3.myworkdayjobs.com/wday/cxs/{tenant}/{site}"

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        with safe_urlopen(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "JoBot/1.0"},
            timeout=self.timeout,
            method="POST",
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return cast(dict[str, Any], data)

    def discover(
        self,
        company: str,
        keywords: str = "",
        location: str = "",
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch real job postings for a Workday tenant via the cxs /jobs API."""
        tenant, site = self._split_company(company)
        url = f"{self._cxs_base(tenant, site)}/jobs"
        search_text = keywords or location
        payload: dict[str, Any] = {"appliedFacets": {}, "limit": limit, "offset": 0}
        if search_text:
            payload["searchText"] = search_text
        try:
            data = self._post_json(url, payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WORKDAY DISCOVERY] cxs /jobs failed for %s: %s", company, exc)
            return []
        postings = data.get("jobPostings", []) or []
        if not isinstance(postings, list):
            return []
        return postings[:limit]

    def job_posting(self, company: str, job_id: str) -> dict[str, Any]:
        """Fetch a single job posting via the cxs jobPosting API. Raises on failure."""
        tenant, site = self._split_company(company)
        url = f"{self._cxs_base(tenant, site)}/jobPosting/{job_id}"
        return self._post_json(url, {"limit": 1, "offset": 0})


class WorkdaySubmitter:
    """Workday real application submission via Patchright (no fabrication)."""

    async def _page_text(self, page: Any) -> str:
        try:
            body = page.locator("body")
            texts = await body.all_text_contents()
            return " ".join(texts).lower()
        except Exception:  # noqa: BLE001
            return ""

    async def _click_first(self, page: Any, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    await locator.first.click()
                    return True
            except Exception:  # noqa: BLE001, S112 — best-effort click across a selector ladder; failure of one selector is not actionable for callers
                continue
        return False

    async def _find_marker(self, page: Any, markers: list[str]) -> bool:
        text = await self._page_text(page)
        return any(marker in text for marker in markers)

    async def submit(self, application: Application, page: Any | None = None) -> bool:
        if page is None:
            logger.warning("[WORKDAY] No live browser page — refusing to fabricate a submission.")
            return False
        if not application.job_url:
            logger.warning("[WORKDAY] No job_url on application — cannot apply.")
            return False

        try:
            await page.goto(application.job_url, wait_until="domcontentloaded")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WORKDAY] goto %s failed: %s", application.job_url, exc)
            return False

        if await self._find_marker(page, ALREADY_APPLIED_MARKERS):
            application.status = ApplicationStatus.DUPLICATE_SKIPPED
            return False

        applied = await self._click_first(page, APPLY_BUTTON_SELECTORS)
        if not applied:
            if await self._find_marker(page, CONFIRMATION_MARKERS):
                application.status = ApplicationStatus.SUBMITTED
                return True
            logger.warning("[WORKDAY] No apply button found on posting.")
            return False

        await self._click_first(page, GUEST_CONTINUE_SELECTORS)

        submitted = await self._click_first(page, SUBMIT_BUTTON_SELECTORS)
        if not submitted:
            logger.warning("[WORKDAY] No submit button found after applying.")
            return False

        if await self._find_marker(page, CONFIRMATION_MARKERS):
            application.status = ApplicationStatus.SUBMITTED
            return True
        logger.warning("[WORKDAY] No confirmation marker observed after submit.")
        return False


class WorkdayVerifier:
    """Workday real submission verification via candidate portal (no fabrication)."""

    async def verify(
        self,
        application: Application,
        page: Any | None = None,
        job_title: str | None = None,
    ) -> VerificationResult:
        if page is None:
            return VerificationResult(
                success=False,
                confidence=0.0,
                confirmation_id="",
                reason="No live browser page — cannot verify a Workday submission.",
            )
        try:
            if not application.job_url:
                return VerificationResult(
                    success=False,
                    confidence=0.0,
                    reason="No job_url on application — cannot verify.",
                )
            await page.goto(application.job_url, wait_until="domcontentloaded")
        except Exception as exc:  # noqa: BLE001
            return VerificationResult(
                success=False,
                confidence=0.0,
                reason=f"Could not load posting for verification: {exc}",
            )
        try:
            text = await page.locator("body").inner_text()
            lowered = text.lower()
        except Exception:  # noqa: BLE001
            return VerificationResult(
                success=False, confidence=0.0, reason="Could not read posting page."
            )
        if any(marker in lowered for marker in ALREADY_APPLIED_MARKERS) or any(
            marker in lowered for marker in CONFIRMATION_MARKERS
        ):
            return VerificationResult(
                success=True,
                confidence=0.8,
                confirmation_id=application.job_id,
                reason="Workday posting reflects an applied/submitted state.",
            )
        return VerificationResult(
            success=False,
            confidence=0.0,
            reason="Posting page shows no applied/submitted state.",
        )


class WorkdayAdapter(SiteAdapter):
    """Honest Workday ATS adapter: cxs-API discovery/parse, Patchright submit/verify."""

    capabilities = AdapterCapability.FULL_BROWSER

    def __init__(self) -> None:
        super().__init__("workday")
        self.api = WorkdayApi()
        self.submitter = WorkdaySubmitter()
        self.verifier = WorkdayVerifier()
        self._session: BrowserSession | None = None

    def _live_enabled(self) -> bool:
        return os.getenv("JOBOT_RUN_LIVE_BROWSER") == "1"

    async def _browser_page(self) -> Any | None:
        if not self._live_enabled():
            logger.warning(
                "[WORKDAY] Live browser disabled (JOBOT_RUN_LIVE_BROWSER=1 to enable) — "
                "refusing to fabricate submit/verify."
            )
            return None
        if self._session is None:
            self._session = BrowserSession(portal="workday", headless=True)
            await self._session.start()
        return await self._session.new_page()

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        logger.warning(
            "[WORKDAY] Login is tenant SSO; this adapter does not automate credentials. "
            "Use 'jobot login' with a real browser session if available."
        )
        return False

    def _posting_from_api(self, info: dict[str, Any], url: str, company: str) -> JobPosting:
        description = info.get("jobDescription", "") or ""
        description_text = re.sub(r"<[^>]+>", " ", description)
        description_text = html.unescape(" ".join(description_text.split()))
        return JobPosting(
            job_id=str(info.get("jobPostingId") or ""),
            site="workday",
            url=url,
            title=info.get("jobPostingTitle") or "",
            company=company,
            location=info.get("locationsText") or "",
            description=description_text,
            raw_html=description,
            parsed_skills=[],
            discovered_at=_now(),
        )

    async def parse_job_posting(self, url: str) -> JobPosting:
        try:
            tenant, site = self.api._tenant_site_from_url(url)
        except ValueError:
            raise
        job_id = self.api._job_id_from_url(url)
        if not job_id:
            raise ValueError(f"Could not resolve a Workday job id from URL: {url}")
        try:
            data = self.api.job_posting(f"{tenant}.{site}", job_id)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Workday cxs jobPosting fetch failed for {url}: {exc}") from exc
        info = data.get("jobPostingInfo")
        if not info or not info.get("jobPostingTitle"):
            raise RuntimeError(f"Workday posting returned no parseable job info for {url}")
        external = info.get("externalUrl") or url
        return self._posting_from_api(info, external, tenant)

    async def discover_jobs(
        self,
        keywords: str = "",
        location: str = "",
        limit: int = 25,
        company: str | None = None,
    ) -> list[JobPosting]:
        if not company:
            logger.warning(
                "[WORKDAY] discover_jobs requires a company/tenant (e.g. company='toptal'); "
                "skipping generic discovery."
            )
            return []
        try:
            raw = self.api.discover(
                company=company, keywords=keywords, location=location, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WORKDAY DISCOVERY] Failed for %s: %s", company, exc)
            return []
        tenant, site = self.api._split_company(company)
        postings: list[JobPosting] = []
        for item in raw:
            external_path = item.get("externalPath") or ""
            if not item.get("title"):
                continue
            posting_url = (
                f"https://{tenant}.wd3.myworkdayjobs.com{external_path}"
                if external_path
                else f"https://{tenant}.wd3.myworkdayjobs.com/{site}/job/{item.get('id', '')}"
            )
            postings.append(
                JobPosting(
                    job_id=str(item.get("id") or ""),
                    site="workday",
                    url=posting_url,
                    title=item.get("title", ""),
                    company=tenant,
                    location=item.get("locationsText") or "",
                    description="",
                    parsed_skills=[],
                    discovered_at=_now(),
                )
            )
        return postings

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> dict[str, Any]:
        info = profile.personal_info
        filled: dict[str, Any] = {
            "first_name": info.first_name,
            "last_name": info.last_name,
            "name": f"{info.first_name} {info.last_name}".strip(),
            "email": info.email,
            "phone": info.phone,
        }
        if info.location_city:
            filled["address_city"] = info.location_city
        application.form_values = filled
        application.status = ApplicationStatus.FILLED
        return filled

    async def submit_application(self, application: Application) -> bool:
        page = await self._browser_page()
        return await self.submitter.submit(application, page=page)

    async def verify_submission(self, application: Application) -> VerificationResult:
        page = await self._browser_page()
        return await self.verifier.verify(application, page=page)
