"""Lever ATS adapter — real API (Phase 3, T3.5).

Discovery delegates to the scrapers family LeverAdapter (real postings from
api.lever.co/v0/postings). Parsing, submission, and verification hit the real
Lever public postings API. Verification is honest: a confirmation is only
reported when the API actually returns an application record.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from jobot.adapters.base import SiteAdapter
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.security.url_guard import safe_urlopen

logger = logging.getLogger(__name__)

API_BASE = "https://api.lever.co/v0/postings"


class LeverAdapter(SiteAdapter):
    """
    Lever ATS Adapter (direct API). Zero fabrication: every method either
    returns real API data or raises an explicit error.
    """

    def __init__(self) -> None:
        super().__init__("lever")

    # -- URL helpers --------------------------------------------------------

    def _extract_company_and_posting(self, url: str) -> tuple[str, str]:
        """Extract (company, posting_id) from a Lever posting URL."""
        parts = [p for p in url.rstrip("/").split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Cannot extract company/posting from Lever URL: {url}")
        company, posting_id = parts[-2], parts[-1]
        if not company or not posting_id:
            raise ValueError(f"Cannot extract company/posting from Lever URL: {url}")
        return company, posting_id

    def _get_json(self, url: str) -> Dict[str, Any]:
        with safe_urlopen(url, headers={"User-Agent": "JoBot/1.0"}, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _post_json(self, url: str, payload: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        req_data = json.dumps(payload).encode("utf-8")
        with safe_urlopen(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "User-Agent": "JoBot/1.0"},
            timeout=10.0,
            method="POST",
        ) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return resp.status, parsed

    # -- SiteAdapter API ----------------------------------------------------

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        # Lever public postings API requires no authentication for applications.
        return True

    async def parse_job_posting(self, url: str) -> JobPosting:
        company, posting_id = self._extract_company_and_posting(url)
        data = self._get_json(f"{API_BASE}/{company}/{posting_id}?mode=json")
        if not data or not data.get("id"):
            raise ValueError(f"Lever API returned no posting for {company}/{posting_id}")
        location = ""
        cats = data.get("categories") or {}
        if isinstance(cats.get("location"), dict):
            loc = cats["location"]
            location = (
                str(loc.get("full") or "")
                if loc.get("full")
                else ", ".join(str(x) for x in (loc.get("city"), loc.get("country")) if x)
            )
        skills = [
            item.get("text", "")
            for item in (data.get("lists") or [])
            if isinstance(item, dict) and item.get("text")
        ]
        return JobPosting(
            job_id=str(data.get("id", posting_id)),
            site="lever",
            url=url,
            title=str(data.get("text") or data.get("title") or "Untitled"),
            company=company,
            location=location,
            description=str(data.get("descriptionPlain") or data.get("description") or ""),
            parsed_skills=skills,
            discovered_at=datetime.now(timezone.utc),
        )

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        filled_data = {
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip(),
            "email": profile.personal_info.email,
            "phone": profile.personal_info.phone,
            "org": profile.custom_qa_answers.get("Current Employer", ""),
            "urls": {"LinkedIn": profile.personal_info.linkedin_url or ""},
        }
        if application.form_values and application.form_values.get("cover_letter_text"):
            filled_data["comments"] = application.form_values["cover_letter_text"]
        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        return filled_data

    async def submit_application(self, application: Application) -> bool:
        job_url = getattr(application, "job_url", "") or application.site
        company, posting_id = self._extract_company_and_posting(job_url)
        payload = {
            "name": application.form_values.get("name"),
            "email": application.form_values.get("email"),
            "phone": application.form_values.get("phone"),
            "org": application.form_values.get("org") or "",
            "urls": application.form_values.get("urls") or {},
        }
        if application.form_values.get("comments"):
            payload["comments"] = application.form_values["comments"]
        try:
            status, body = self._post_json(
                f"{API_BASE}/{company}/{posting_id}/applications", payload
            )
            if status not in (200, 201):
                application.status = ApplicationStatus.FAILED
                application.error_message = f"Lever POST status {status}"
                return False
            confirmation = body.get("id") if isinstance(body, dict) else None
            if confirmation:
                application.form_values["_lever_confirmation_id"] = str(confirmation)
            application.status = ApplicationStatus.SUBMITTED
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("[LEVER SUBMIT API ERROR] %s: %s", job_url, exc)
            application.status = ApplicationStatus.FAILED
            application.error_message = f"Lever API error: {exc}"
            return False

    async def verify_submission(self, application: Application) -> VerificationResult:
        confirmation = (application.form_values or {}).get("_lever_confirmation_id")
        if confirmation:
            application.status = ApplicationStatus.VERIFIED
            return VerificationResult(
                success=True,
                confidence=0.9,
                confirmation_id=str(confirmation),
                reason="Lever API returned an application record on submit",
            )
        return VerificationResult(
            success=False,
            confidence=0.0,
            confirmation_id="",
            reason="Lever API returned no confirmation record; submission outcome unknown",
        )
