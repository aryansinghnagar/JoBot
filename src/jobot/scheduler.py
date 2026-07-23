import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SchedulerManager:
    """
    Cron-like Job Scheduler Manager (Layer C).
    Persists recurring campaign schedules to ~/.jobot/schedules.json.
    """

    def __init__(self, schedule_file: Optional[Path] = None):
        if schedule_file is None:
            schedule_file = Path.home() / ".jobot" / "schedules.json"
        self.schedule_file = schedule_file
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)

    def list_schedules(self) -> List[Dict[str, Any]]:
        """Load persisted schedule entries."""
        if not self.schedule_file.exists():
            return []
        try:
            return json.loads(self.schedule_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def add_schedule(self, cron_expr: str, command: str) -> Dict[str, Any]:
        """Add a recurring cron schedule entry."""
        schedules = self.list_schedules()
        sched_id = f"sch_{len(schedules) + 1:03d}"
        entry = {
            "schedule_id": sched_id,
            "cron": cron_expr,
            "command": command,
            "active": True,
        }
        schedules.append(entry)
        self.schedule_file.write_text(json.dumps(schedules, indent=2), encoding="utf-8")
        return entry

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule entry by ID."""
        schedules = self.list_schedules()
        filtered = [s for s in schedules if s.get("schedule_id") != schedule_id]
        if len(filtered) < len(schedules):
            self.schedule_file.write_text(json.dumps(filtered, indent=2), encoding="utf-8")
            return True
        return False
