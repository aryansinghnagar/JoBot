"""Job discovery and portal commands for JoBot CLI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def format_jobs_table(jobs: list[Any], title: str = "Discovered Jobs") -> Table:
    """Format discovered jobs list as a Rich table."""
    table = Table(title=title)
    table.add_column("Title", style="cyan")
    table.add_column("Company", style="bold")
    table.add_column("Site", style="magenta")
    table.add_column("Location", style="dim")
    table.add_column("Match Score", justify="right")

    for job in jobs:
        score_str = (
            f"{job.match_score:.0%}" if hasattr(job, "match_score") and job.match_score else "N/A"
        )
        loc = getattr(job, "location", "") or ""
        table.add_row(
            getattr(job, "title", "N/A"),
            getattr(job, "company", "N/A"),
            getattr(job, "site", "N/A"),
            loc,
            score_str,
        )
    return table
