import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from jobot.models.domain import Application, JobPosting


class ApplicationMarkdownLogger:
    """
    Project Root log.md Maintainer (Layer L).
    Logs all application submissions into `log.md` at project root, sectioned by date.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            root_dir = Path.cwd()
        self.log_md_path = root_dir / "log.md"

    def log_submission(
        self,
        application: Application,
        job: JobPosting,
        match_score: float = 1.0,
    ) -> None:
        """Append application submission entry to log.md at project root."""
        today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        timestamp_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

        file_exists = self.log_md_path.exists()
        content = ""

        if file_exists:
            content = self.log_md_path.read_text(encoding="utf-8")
        else:
            content = "# JoBot Application Execution Log\n\nOfficial audit record of all automated job applications submitted by JoBot.\n\n"

        date_section = f"## {today_date}"
        table_header = "| App ID | Portal | Job Title | Company | Match Score | Status | Time |\n|--------|--------|-----------|---------|-------------|--------|------|"

        if date_section not in content:
            # Create new date section
            content += f"\n{date_section}\n\n{table_header}\n"

        # Format new table row
        new_row = f"| `{application.application_id[:8]}` | **{job.site.upper()}** | {job.title} | {job.company} | {int(match_score * 100)}% | `{application.status.value.upper()}` | {timestamp_time} |\n"

        content += new_row
        self.log_md_path.write_text(content, encoding="utf-8")
