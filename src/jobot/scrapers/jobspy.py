"""JobSpy board adapter (plan.md Phase 2).

Wraps the `python-jobspy` library (`from jobspy import scrape_jobs`) behind
JoBot's circuit breaker and politeness delays. The library is NOT a declared
dependency (its metadata pins NUMPY==1.26.3, which cannot resolve on modern
Python); it is installed via the documented `--no-deps` recipe (SETUP.md) and
import-guarded here with a clear error.
"""

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from jobot.models.domain import JobPosting
from jobot.scrapers.exceptions import JobSpyNotInstalledError
from jobot.stealth.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

JOBS_BOARDS = (
    "linkedin",
    "indeed",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
    "bdjobs",
)


def _cell(row: Any, key: str, default: Any = "") -> Any:
    """Read a cell from a pandas Series or plain dict without importing pandas."""
    try:
        value = row[key]
    except (KeyError, TypeError):
        return default
    if value is None:
        return default
    if isinstance(value, float) and value != value:  # NaN
        return default
    return value


class JobSpyAdapter:
    """Scrapes one job board via JobSpy, behind a circuit breaker."""

    def __init__(
        self,
        board: str,
        delay_s: float = 1.0,
        proxies: Optional[List[str]] = None,
        breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        if board not in JOBS_BOARDS:
            raise ValueError(f"Unknown JobSpy board '{board}'. Supported: {JOBS_BOARDS}")
        self.board = board
        self.delay_s = delay_s
        self.proxies = proxies
        self.breaker = breaker or CircuitBreaker()

    def _domain(self) -> str:
        return f"jobspy:{self.board}"

    @staticmethod
    def _load_jobspy() -> Any:
        try:
            from jobspy import scrape_jobs  # noqa: PLC0415
        except ModuleNotFoundError as exc:
            if exc.name == "jobspy":
                raise JobSpyNotInstalledError() from exc
            raise
        return scrape_jobs

    async def _scrape(
        self,
        keywords: str,
        location: str,
        limit: int,
        hours_old: Optional[int],
        country_indeed: str,
        is_remote: bool,
        job_type: Optional[str],
    ) -> Any:
        scrape_jobs = self._load_jobspy()
        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)
        kwargs: Dict[str, Any] = {
            "site_name": self.board,
            "search_term": keywords or None,
            "location": location or None,
            "results_wanted": limit,
            "hours_old": hours_old,
            "verbose": False,
        }
        if self.board == "indeed":
            kwargs["country_indeed"] = country_indeed
        if self.board == "google":
            kwargs["google_search_term"] = keywords or None
        if is_remote:
            kwargs["is_remote"] = True
        if job_type:
            kwargs["job_type"] = job_type
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return await asyncio.to_thread(scrape_jobs, **kwargs)

    async def discover_jobs(
        self,
        keywords: str = "",
        location: str = "",
        limit: int = 25,
        hours_old: Optional[int] = 72,
        country_indeed: str = "USA",
        is_remote: bool = False,
        job_type: Optional[str] = None,
    ) -> List[JobPosting]:
        """Scrape postings from the board through the circuit breaker."""
        frame = await self.breaker.execute_with_retry(
            self._domain(),
            self._scrape,
            keywords,
            location,
            limit,
            hours_old,
            country_indeed,
            is_remote,
            job_type,
        )
        if frame is None:
            return []
        postings: List[JobPosting] = []
        for _, row in frame.iterrows():
            url = str(_cell(row, "job_url") or "")
            title = str(_cell(row, "title") or "").strip()
            if not title:
                continue
            company = str(_cell(row, "company_name") or "")
            if not url:
                digest = hashlib.sha256(f"{self.board}|{title}|{company}".encode()).hexdigest()[:16]
                url = f"https://{self.board}.jobs/job/{digest}"
            postings.append(
                JobPosting(
                    job_id=url,
                    site=self.board,
                    url=url,
                    title=title,
                    company=company,
                    location=str(_cell(row, "location") or ""),
                    description=str(_cell(row, "description") or ""),
                    parsed_skills=[],
                )
            )
        logger.info("JobSpy board '%s' returned %d postings", self.board, len(postings))
        return postings
