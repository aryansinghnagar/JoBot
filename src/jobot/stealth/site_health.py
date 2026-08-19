"""Site Health Monitor and Failure Tracker (UC-13).

Tracks availability, success rates, latency, and degradation states per portal.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SiteHealthStatus(BaseModel):
    site: str
    status: str = "HEALTHY"  # "HEALTHY", "DEGRADED", "TRIPPED"
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: float = 0.0
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error: str | None = None

    @property
    def total_requests(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests

    @property
    def avg_latency_ms(self) -> float:
        if self.success_count == 0:
            return 0.0
        return self.total_latency_ms / self.success_count


class SiteHealthMonitor:
    """In-memory & persistent health tracker across portals."""

    def __init__(self, failure_trip_threshold: int = 5) -> None:
        self.trip_threshold = failure_trip_threshold
        self._stats: dict[str, SiteHealthStatus] = {}

    def get_status(self, site: str) -> SiteHealthStatus:
        s = site.lower().strip()
        if s not in self._stats:
            self._stats[s] = SiteHealthStatus(site=s)
        return self._stats[s]

    def record_success(self, site: str, latency_ms: float = 0.0) -> None:
        st = self.get_status(site)
        st.success_count += 1
        st.consecutive_failures = 0
        st.total_latency_ms += latency_ms
        st.last_success_at = datetime.now(UTC).isoformat()
        if st.status == "TRIPPED" or st.status == "DEGRADED":
            st.status = "HEALTHY"

    def record_failure(self, site: str, error_msg: str) -> None:
        st = self.get_status(site)
        st.failure_count += 1
        st.consecutive_failures += 1
        st.last_failure_at = datetime.now(UTC).isoformat()
        st.last_error = error_msg[:300]

        if st.consecutive_failures >= self.trip_threshold:
            st.status = "TRIPPED"
        elif st.consecutive_failures >= 2:
            st.status = "DEGRADED"

    def list_all_statuses(self) -> list[SiteHealthStatus]:
        return list(self._stats.values())


__all__ = ["SiteHealthMonitor", "SiteHealthStatus"]
