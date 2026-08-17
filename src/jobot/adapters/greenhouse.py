import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from jobot.adapters.base import SiteAdapter
from jobot.adapters.capabilities import AdapterCapability
from jobot.models.domain import (
    Application,
    ApplicationStatus,
    JobPosting,
    UserProfile,
    VerificationResult,
)
from jobot.security.url_guard import safe_urlopen, validate_fetch_url, validate_path_segment

logger = logging.getLogger(__name__)


class GreenhouseAdapter(SiteAdapter):
    """
    Greenhouse ATS Adapter (Layer 5).
    Leverages Greenhouse Public Boards API (boards-api.greenhouse.io) for job parsing,
    board discovery, and direct API POST application submissions.
    """

    capabilities = AdapterCapability.FULL_API

    BASE_API_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self) -> None:
        super().__init__("greenhouse")

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        # Greenhouse Public API requires zero user authentication
        return True

    def _extract_board_and_job_id(self, url: str) -> tuple[str, str]:
        """Extract board token and job ID from Greenhouse URL."""
        # Example URLs:
        # https://boards.greenhouse.io/acme/jobs/12345
        # https://boards-api.greenhouse.io/v1/boards/acme/jobs/12345
        parts = url.rstrip("/").split("/")
        if "jobs" in parts:
            idx = parts.index("jobs")
            board = parts[idx - 1] if idx > 0 else "default"
            job_id = parts[idx + 1] if idx + 1 < len(parts) else str(uuid.uuid4())
            return board, job_id
        return "default", str(uuid.uuid4())

    async def parse_job_posting(self, url: str) -> JobPosting:
        board, job_id = self._extract_board_and_job_id(url)
        board = validate_path_segment(board)
        job_id = validate_path_segment(job_id)
        api_url = validate_fetch_url(f"{self.BASE_API_URL}/{board}/jobs/{job_id}")

        with safe_urlopen(api_url, headers={"User-Agent": "JoBot/1.0"}, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return JobPosting(
                job_id=str(data.get("id", job_id)),
                site="greenhouse",
                url=url,
                title=data.get("title", "Software Engineer"),
                company=board.capitalize(),
                location=data.get("location", {}).get("name", "Remote"),
                description=data.get("content", ""),
                parsed_skills=[],
                discovered_at=datetime.now(timezone.utc),
            )

    async def discover_matching_jobs(
        self, board_token: str = "greenhouse", limit: int = 5
    ) -> List[JobPosting]:
        """Fetch job postings for a specific Greenhouse board token via API."""
        return await self.discover_jobs(company=board_token, limit=limit)

    async def discover_jobs(
        self,
        company: str,
        limit: int = 25,
        keywords: str = "",
        location: str = "",
    ) -> List[JobPosting]:
        """Fetch real postings for a Greenhouse board; empty on failure (no fabrication)."""
        company = validate_path_segment(company)
        api_url = validate_fetch_url(f"{self.BASE_API_URL}/{company}/jobs?content=true")
        postings: List[JobPosting] = []

        try:
            with safe_urlopen(api_url, headers={"User-Agent": "JoBot/1.0"}, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                jobs = data.get("jobs", [])[:limit]
                for item in jobs:
                    postings.append(
                        JobPosting(
                            job_id=str(item.get("id")),
                            site="greenhouse",
                            url=item.get(
                                "absolute_url",
                                f"https://boards.greenhouse.io/{company}/jobs/{item.get('id')}",
                            ),
                            title=item.get("title", ""),
                            company=company.capitalize(),
                            location=item.get("location", {}).get("name", ""),
                            description=item.get("content", ""),
                            parsed_skills=[],
                            discovered_at=datetime.now(timezone.utc),
                        )
                    )
        except Exception as e:  # noqa: BLE001
            logger.warning("[GREENHOUSE DISCOVERY API] Error for board %s: %s", company, e)

        if not postings:
            logger.warning("[GREENHOUSE DISCOVERY API] No real postings for board %s", company)
        return postings

    async def fill_form(
        self, job: JobPosting, profile: UserProfile, application: Application
    ) -> Dict[str, Any]:
        filled_data = {
            "first_name": profile.personal_info.first_name,
            "last_name": profile.personal_info.last_name,
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}".strip(),
            "email": profile.personal_info.email,
            "phone": profile.personal_info.phone,
            "linkedin_profile": profile.personal_info.linkedin_url or "",
        }
        application.form_values = filled_data
        application.status = ApplicationStatus.FILLED
        return filled_data

    async def submit_application(self, application: Application) -> bool:
        target_url = getattr(application, "job_url", "") or application.site
        board, job_id = self._extract_board_and_job_id(target_url)
        board = validate_path_segment(board)
        job_id = validate_path_segment(job_id)
        api_url = validate_fetch_url(f"{self.BASE_API_URL}/{board}/jobs/{job_id}/applications")

        payload = {
            "first_name": application.form_values.get("first_name"),
            "last_name": application.form_values.get("last_name"),
            "email": application.form_values.get("email"),
            "phone": application.form_values.get("phone"),
        }
        if application.form_values.get("linkedin_profile"):
            payload["linkedin_profile"] = application.form_values["linkedin_profile"]

        resume_path = application.form_values.get("resume_path") or ""
        if resume_path:
            resume_file = Path(resume_path)
            if resume_file.exists():
                import base64

                payload["resume"] = {
                    "filename": resume_file.name,
                    "content_base64": base64.b64encode(resume_file.read_bytes()).decode("ascii"),
                }
            else:
                logger.warning("resume_path set but file missing: %s", resume_path)

        try:
            req_data = json.dumps(payload).encode("utf-8")
            with safe_urlopen(
                api_url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "JoBot/1.0"},
                timeout=5.0,
                method="POST",
            ) as resp:
                if resp.status in [200, 201]:
                    body = resp.read().decode("utf-8")
                    if body:
                        try:
                            confirmation = json.loads(body).get("id")
                        except json.JSONDecodeError:
                            confirmation = None
                        if confirmation:
                            application.form_values["_greenhouse_confirmation_id"] = str(
                                confirmation
                            )
                    try:
                        from jobot.obs.evidence import BrowserEvidenceCollector

                        collector = BrowserEvidenceCollector()
                        collector.record_api_evidence(
                            application_id=application.application_id,
                            site=self.site_name,
                            confirmation_id=application.form_values.get(
                                "_greenhouse_confirmation_id"
                            ),
                            request_payload=req_data,
                            response_status=resp.status,
                        )
                    except Exception as ev_err:  # noqa: BLE001
                        logger.debug("Failed recording greenhouse API evidence: %s", ev_err)

                    application.status = ApplicationStatus.SUBMITTED
                    return True
                else:
                    application.status = ApplicationStatus.FAILED
                    application.error_message = f"Greenhouse POST status {resp.status}"
                    return False
        except Exception as e:
            logger.warning(f"[GREENHOUSE SUBMIT API ERROR] POST to {api_url} failed: {e}")
            application.status = ApplicationStatus.FAILED
            application.error_message = f"Greenhouse API error: {e}"
            return False

    async def verify_submission(self, application: Application) -> VerificationResult:
        confirmation = (application.form_values or {}).get("_greenhouse_confirmation_id")
        if confirmation:
            application.status = ApplicationStatus.VERIFIED
            return VerificationResult(
                success=True,
                confidence=0.9,
                confirmation_id=str(confirmation),
                reason="Greenhouse API returned an application record on submit",
            )
        return VerificationResult(
            success=False,
            confidence=0.0,
            confirmation_id="",
            reason="Greenhouse API returned no confirmation record; submission outcome unknown",
        )
