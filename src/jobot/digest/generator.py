from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from jobot.storage.db import DatabaseManager
from jobot.tracker.analytics import TrackerAnalytics


@dataclass
class Digest:
    subject: str
    html: str
    text: str


class DigestGenerator:
    """Produce a weekly activity digest from the application control DB.

    Reuses TrackerAnalytics for funnel + by-board + latency; filters recent
    applications to the requested period for the body.
    """

    def __init__(
        self,
        db: DatabaseManager | None = None,
        analytics: TrackerAnalytics | None = None,
        period_days: int = 7,
    ) -> None:
        self.db = db or DatabaseManager()
        self.analytics = analytics or TrackerAnalytics(self.db)
        self.period_days = period_days
        templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )

    def _period_recent(self, now: datetime | None = None) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        cutoff = now - timedelta(days=self.period_days)
        rows = self.analytics.recent(limit=1000)
        out = []
        for r in rows:
            try:
                created = datetime.fromisoformat(r["created_at"])
            except (ValueError, KeyError):
                continue
            if created >= cutoff:
                out.append(r)
        return out

    def generate(self, period_days: int | None = None, now: datetime | None = None) -> Digest:
        if period_days is not None:
            self.period_days = period_days
        now = now or datetime.now(UTC)
        recent = self._period_recent(now=now)
        by_board = self.analytics.by_board()
        funnel = self.analytics.funnel()
        rr = self.analytics.response_rate()
        lat = self.analytics.rejection_latency_days()
        summary = {
            "period_days": self.period_days,
            "generated": now.strftime("%Y-%m-%d %H:%M UTC"),
            "total": len(recent),
            "funnel": funnel,
            "by_board": by_board,
            "response_rate": round(rr, 3),
            "latency_avg_days": lat["avg_days"],
            "latency_count": lat["count"],
            "recent": recent,
        }
        html = self._env.get_template("digest.html.j2").render(**summary)
        text = self._env.get_template("digest.txt.j2").render(**summary)
        subject = f"JoBot weekly digest — {len(recent)} apps ({summary['period_days']} days)"
        return Digest(subject=subject, html=html, text=text)

    def render_file(self, out_path: Path, period_days: int | None = None) -> Path:
        digest = self.generate(period_days=period_days)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(digest.html, encoding="utf-8")
        return out_path
