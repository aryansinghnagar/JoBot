import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jobot.models.domain import ApplicationStatus
from jobot.storage.db import DatabaseManager


TERMINAL_STATUSES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.VERIFIED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.FAILED,
    ApplicationStatus.CANCELLED,
    ApplicationStatus.CIRCUIT_OPEN,
    ApplicationStatus.BLOCKED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TrackerAnalytics:
    """Aggregate application funnel + velocity metrics from the control DB."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def status_counts(self, limit: int = 1000) -> Dict[str, int]:
        rows = self.db.get_applications_with_jobs(limit=limit)
        counts: Dict[str, int] = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        return counts

    def funnel(self, limit: int = 1000) -> Dict[str, int]:
        counts = self.status_counts(limit=limit)
        total = sum(counts.values())
        in_pipeline = sum(
            n
            for status, n in counts.items()
            if status not in {"verified", "rejected", "failed", "cancelled", "circuit_open"}
        )
        return {
            "total": total,
            "in_pipeline": in_pipeline,
            "pending_approval": counts.get("pending_approval", 0),
            "submitted": counts.get("submitted", 0),
            "verified": counts.get("verified", 0),
            "rejected": counts.get("rejected", 0),
            "failed": counts.get("failed", 0),
        }

    def by_board(self, limit: int = 1000) -> List[Dict[str, Any]]:
        rows = self.db.get_applications_with_jobs(limit=limit)
        boards: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            site = r["site"]
            entry = boards.setdefault(
                site, {"site": site, "total": 0, "verified": 0, "rejected": 0, "failed": 0}
            )
            entry["total"] += 1
            entry[r["status"]] = entry.get(r["status"], 0) + 1
        return sorted(boards.values(), key=lambda b: b["total"], reverse=True)

    def response_rate(self, limit: int = 1000) -> float:
        """verified / (verified + rejected) among responded applications."""
        rows = self.db.get_applications_with_jobs(limit=limit)
        responded = sum(1 for r in rows if r["status"] in {"verified", "rejected"})
        verified = sum(1 for r in rows if r["status"] == "verified")
        if responded == 0:
            return 0.0
        return verified / responded

    def rejection_latency_days(self, limit: int = 1000) -> Dict[str, Any]:
        """Average days from created_at to responded_at for responded apps."""
        rows = self.db.get_applications_with_jobs(limit=limit)
        latencies: List[float] = []
        for r in rows:
            if not r["responded_at"]:
                continue
            try:
                created = datetime.fromisoformat(r["created_at"])
                responded = datetime.fromisoformat(r["responded_at"])
            except (ValueError, TypeError):
                continue
            latency = (responded - created).total_seconds() / 86400.0
            if latency >= 0:
                latencies.append(latency)
        if not latencies:
            return {"count": 0, "avg_days": 0.0, "median_days": 0.0}
        return {
            "count": len(latencies),
            "avg_days": round(statistics.mean(latencies), 2),
            "median_days": round(statistics.median(latencies), 2),
        }

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.db.get_applications_with_jobs(limit=limit)

    def summary(self) -> Dict[str, Any]:
        return {
            "funnel": self.funnel(),
            "by_board": self.by_board(),
            "response_rate": round(self.response_rate(), 3),
            "rejection_latency": self.rejection_latency_days(),
        }
