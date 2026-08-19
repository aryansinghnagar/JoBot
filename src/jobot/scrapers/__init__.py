"""Scraper layer (Phase 2): JobSpy boards, direct-API ATS families, career-page scanning, dedup."""

from jobot.scrapers.ats import ATS_FAMILY_BOARDS, AtsFamilyAdapter
from jobot.scrapers.careers import CareerPageScanner
from jobot.scrapers.dedup import DedupResult, DedupService
from jobot.scrapers.exceptions import JobSpyNotInstalledError
from jobot.scrapers.jobspy import JOBS_BOARDS, JobSpyAdapter

__all__ = [
    "ATS_FAMILY_BOARDS",
    "AtsFamilyAdapter",
    "CareerPageScanner",
    "DedupResult",
    "DedupService",
    "JOBS_BOARDS",
    "JobSpyAdapter",
    "JobSpyNotInstalledError",
]
