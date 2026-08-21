from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_CRON_FIELD_RE = re.compile(r"^[0-9a-zA-Z*,\-/]+$")
_CRON_ALIASES = frozenset(
    {"@yearly", "@annually", "@monthly", "@weekly", "@daily", "@midnight", "@hourly", "@reboot"}
)


def validate_cron(cron_expr: str) -> bool:
    """Validate standard 5-field cron syntax or standard alias."""
    expr = cron_expr.strip()
    if expr in _CRON_ALIASES:
        return True
    parts = expr.split()
    if len(parts) != 5:
        return False
    return all(_CRON_FIELD_RE.match(p) for p in parts)


class SchedulerManager:
    """Cron-like Job Scheduler Manager (Layer C).

    Persists recurring campaign schedules to ~/.jobot/schedules.json with
    0600 permissions and monotonic IDs.
    """

    def __init__(self, schedule_file: Path | None = None):
        if schedule_file is None:
            schedule_file = Path.home() / ".jobot" / "schedules.json"
        self.schedule_file = Path(schedule_file)
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)

    def _save_file(self, data: list[dict[str, Any]]) -> None:
        self.schedule_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if os.name == "posix" and self.schedule_file.exists():
            os.chmod(self.schedule_file, 0o600)

    def list_schedules(self) -> list[dict[str, Any]]:
        """Load persisted schedule entries."""
        if not self.schedule_file.exists():
            return []
        try:
            data = json.loads(self.schedule_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def add_schedule(self, cron_expr: str, command: str) -> dict[str, Any]:
        """Add a recurring cron schedule entry with validation and monotonic ID."""
        if not validate_cron(cron_expr):
            raise ValueError(
                f"Invalid cron expression: '{cron_expr}'. Expected standard 5-part expression (e.g. '0 9 * * *') or alias."
            )

        schedules = self.list_schedules()
        # Monotonic ID calculation: avoid collisions on deletion
        max_id = 0
        for s in schedules:
            sid = str(s.get("schedule_id", ""))
            match = re.search(r"sch_(\d+)", sid)
            if match:
                try:
                    max_id = max(max_id, int(match.group(1)))
                except ValueError:
                    pass

        sched_id = f"sch_{max_id + 1:03d}"
        entry = {
            "schedule_id": sched_id,
            "cron": cron_expr.strip(),
            "command": command.strip(),
            "active": True,
        }
        schedules.append(entry)
        self._save_file(schedules)
        return entry

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule entry by ID."""
        schedules = self.list_schedules()
        filtered = [s for s in schedules if s.get("schedule_id") != schedule_id]
        if len(filtered) < len(schedules):
            self._save_file(filtered)
            return True
        return False
