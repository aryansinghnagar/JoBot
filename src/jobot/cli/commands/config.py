"""Config management commands for JoBot CLI."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def format_config_table(config_dict: dict[str, Any]) -> Table:
    """Format configuration dictionary as a Rich table."""
    table = Table(title="JoBot Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for section, values in config_dict.items():
        if isinstance(values, dict):
            for k, v in values.items():
                table.add_row(f"{section}.{k}", str(v))
        else:
            table.add_row(section, str(values))
    return table
