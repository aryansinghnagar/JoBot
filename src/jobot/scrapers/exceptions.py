"""Exceptions for the scraper layer."""


class JobFetchError(Exception):
    """Raised when a live job source (board API, career page) cannot be fetched."""


class JobSpyNotInstalledError(RuntimeError):
    """Raised when the jobspy library is required but not installed."""

    def __init__(self) -> None:
        super().__init__(
            "The jobspy scraper library is not installed. Install the scrapers extra and the "
            "pinned library per SETUP.md (Scraping section): "
            "`pip install -e .[scrapers]` then `pip install python-jobspy==1.1.82 --no-deps`."
        )
