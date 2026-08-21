"""CLI modular sub-commands sub-package."""

from jobot.cli.commands.config import format_config_table
from jobot.cli.commands.discovery import format_jobs_table
from jobot.cli.commands.system import format_health_table, version_command
from jobot.cli.commands.tracker import format_tracker_table

__all__ = [
    "format_config_table",
    "format_health_table",
    "format_jobs_table",
    "format_tracker_table",
    "version_command",
]
