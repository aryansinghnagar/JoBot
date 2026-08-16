"""Deterministic LinkedIn people-search URL generation (no scraping)."""

from typing import Optional
from urllib.parse import quote_plus


class LinkedInPeopleSearchURLBuilder:
    """Builds LinkedIn people-search URLs from contact + optional filters.

    Pure URL generation — no browser automation or data collection.
    """

    BASE = "https://www.linkedin.com/search/results/people/"

    def build(
        self,
        keywords: str,
        location: Optional[str] = None,
        current_company: Optional[str] = None,
        title: Optional[str] = None,
    ) -> str:
        params = {"keywords": keywords, "origin": "GLOBAL_SEARCH_HEADER"}
        if location:
            params["location"] = location
        if current_company:
            params["currentCompany"] = current_company
        if title:
            params["title"] = title
        query = "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
        return f"{self.BASE}?{query}"

    def build_for_contact(self, name: str, company: str = "", role: str = "") -> str:
        return self.build(
            keywords=name,
            current_company=company or None,
            title=role or None,
        )
