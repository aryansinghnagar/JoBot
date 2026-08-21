"""System diagnostics and health commands for JoBot CLI."""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from jobot import __version__

console = Console()


def version_command() -> None:
    """Print the JoBot version and system info."""
    console.print(f"[bold cyan]JoBot[/bold cyan] version [green]{__version__}[/green]")
    console.print(f"Python {sys.version.split()[0]} on {sys.platform}")


def format_health_table(checks: dict[str, Any]) -> Table:
    """Render system doctor health checks as a Rich table."""
    table = Table(title="JoBot System Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for name, data in checks.items():
        status = "[green]OK[/green]" if data.get("ok") else "[red]FAIL[/red]"
        details = data.get("details", "")
        table.add_row(name, status, details)
    return table
