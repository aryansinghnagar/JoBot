import logging
from typing import Dict, List, Optional
from pydantic import BaseModel
from jobot.storage.db import DatabaseManager

logger = logging.getLogger(__name__)


class PortalMetrics(BaseModel):
    site: str
    total_attempts: int
    successful_submissions: int
    success_rate: float
    recommended_retry_delay_seconds: float


class EvalOptimizer:
    """
    Self-Improvement Eval Optimizer (Layer I).
    Analyzes historical application submission trajectories and auto-tunes per-portal execution policies.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def analyze_portal_performance(self) -> Dict[str, PortalMetrics]:
        """Compute success rates and auto-tuned delay policies for all portals."""
        apps = self.db.list_applications(limit=1000)
        portal_data: Dict[str, Dict[str, int]] = {}

        for app in apps:
            site = app.site.lower()
            if site not in portal_data:
                portal_data[site] = {"total": 0, "success": 0}

            portal_data[site]["total"] += 1
            if app.status.value in ["submitted", "verified"]:
                portal_data[site]["success"] += 1

        results = {}
        for site, counts in portal_data.items():
            total = counts["total"]
            success = counts["success"]
            rate = success / total if total > 0 else 1.0

            # Auto-tune delay policy based on success rate
            delay = 2.0 if rate >= 0.9 else (5.0 if rate >= 0.7 else 10.0)

            results[site] = PortalMetrics(
                site=site,
                total_attempts=total,
                successful_submissions=success,
                success_rate=rate,
                recommended_retry_delay_seconds=delay,
            )
        return results
