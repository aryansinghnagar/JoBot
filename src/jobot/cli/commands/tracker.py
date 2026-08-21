"""Application tracker and metrics commands for JoBot CLI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def format_tracker_table(applications: list[dict[str, Any]]) -> Table:
    """Format application status records as a Rich table."""
    table = Table(title="Application History")
    table.add_column("App ID", style="dim")
    table.add_column("Company", style="bold")
    table.add_column("Role", style="cyan")
    table.add_column("Site", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Updated", style="dim")

    for app in applications:
        table.add_row(
            str(app.get("id", "N/A"))[:8],
            str(app.get("company", "N/A")),
            str(app.get("job_title", "N/A")),
            str(app.get("site", "N/A")),
            str(app.get("status", "N/A")),
            str(app.get("updated_at", ""))[:19],
        )
    return table
