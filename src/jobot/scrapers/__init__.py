"""Scraper layer (Phase 2): JobSpy boards, direct-API ATS families, career-page scanning, dedup."""

from jobot.scrapers.dedup import DedupService, DedupResult
from jobot.scrapers.exceptions import JobSpyNotInstalledError
from jobot.scrapers.jobspy import JOBS_BOARDS, JobSpyAdapter
from jobot.scrapers.ats import AtsFamilyAdapter, ATS_FAMILY_BOARDS
from jobot.scrapers.careers import CareerPageScanner

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
