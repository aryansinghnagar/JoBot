import json
import logging
import os
import platform
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from jobaut.failure.catalog import FailureMode
from jobaut.obs.tracing import IncidentSeverity

logger = logging.getLogger(__name__)


class ManualTestIssue(BaseModel):
    issue_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    issue_type: str  # "ERROR", "VULNERABILITY", "DOM_DRIFT", "POLICY_VIOLATION", "USER_REPORT"
    summary: str
    details: str
    site: Optional[str] = None
    stack_trace: Optional[str] = None
    system_info: Dict[str, str] = Field(default_factory=dict)
    reproduction_steps: List[str] = Field(default_factory=list)


class ManualTestLogger:
    """
    Manual Testing Telemetry & Bug Logger.
    Captures runtime errors, vulnerabilities, and manual tester feedback during exploratory testing.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path.home() / ".jobaut" / "manual_test_logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.jsonl_file = self.log_dir / "issues.jsonl"
        self.markdown_report = self.log_dir / "manual_test_report.md"

    def _get_system_info(self) -> Dict[str, str]:
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version.split()[0],
            "working_directory": str(Path.cwd()),
        }

    def log_issue(
        self,
        summary: str,
        issue_type: str = "ERROR",
        details: str = "",
        site: Optional[str] = None,
        exc: Optional[BaseException] = None,
        reproduction_steps: Optional[List[str]] = None,
    ) -> ManualTestIssue:
        """Record an issue, exception, or security vulnerability detected during manual testing."""
        tb_str = None
        if exc is not None:
            tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        issue = ManualTestIssue(
            issue_id=f"TEST-BUG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.urandom(2).hex()}",
            issue_type=issue_type,
            summary=summary,
            details=details,
            site=site,
            stack_trace=tb_str,
            system_info=self._get_system_info(),
            reproduction_steps=reproduction_steps or [],
        )

        # Write to JSONL
        with open(self.jsonl_file, "a", encoding="utf-8") as f:
            f.write(issue.model_dump_json() + "\n")

        # Append to Markdown Summary Report
        self._append_markdown_report(issue)

        logger.info(f"[ManualTestLogger] Recorded {issue_type}: {summary} ({issue.issue_id})")
        return issue

    def _append_markdown_report(self, issue: ManualTestIssue) -> None:
        header_needed = not self.markdown_report.exists()
        with open(self.markdown_report, "a", encoding="utf-8") as f:
            if header_needed:
                f.write("# Manual Testing Diagnostic & Bug Log\n\n")
                f.write("Log of errors, vulnerabilities, and issues recorded during manual testing sessions.\n\n")
                f.write("| Issue ID | Type | Site | Summary | Timestamp |\n")
                f.write("|----------|------|------|---------|-----------|\n")

            f.write(
                f"| `{issue.issue_id}` | **{issue.issue_type}** | {issue.site or 'General'} | {issue.summary} | {issue.timestamp.strftime('%Y-%m-%d %H:%M:%S')} |\n"
            )

    def list_issues(self) -> List[ManualTestIssue]:
        """List all recorded manual test issues."""
        if not self.jsonl_file.exists():
            return []

        issues = []
        with open(self.jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        issues.append(ManualTestIssue.model_validate_json(line))
                    except Exception as e:
                        logger.error(f"Failed to parse issue line: {e}")
        return issues
