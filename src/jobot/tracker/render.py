from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from jobot.tracker.analytics import TrackerAnalytics


class TrackerRenderer:
    """Render tracking analytics to a terminal table or standalone HTML."""

    def __init__(self, analytics: TrackerAnalytics) -> None:
        self.analytics = analytics
        templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )

    def terminal_rows(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.analytics.recent(limit=limit)

    def render_terminal(self, console: Any, limit: int = 20) -> None:
        from rich.table import Table

        rows = self.terminal_rows(limit=limit)
        table = Table(title="Applications")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Site")
        table.add_column("Title", overflow="fold")
        table.add_column("Company")
        table.add_column("Status", style="bold")
        table.add_column("Created")
        table.add_column("Responded")
        table.add_column("Outcome")
        for i, r in enumerate(rows, start=1):
            created = r["created_at"][:16] if r["created_at"] else ""
            responded = r["responded_at"][:16] if r["responded_at"] else ""
            table.add_row(
                str(i),
                r["site"],
                r["title"],
                r["company"],
                r["status"],
                created,
                responded,
                r["outcome"] or "",
            )
        console.print(table)

        fun = self.analytics.funnel()
        console.print(
            f"[bold cyan]Funnel:[/bold cyan] {fun['total']} total | "
            f"{fun['pending_approval']} pending approval | "
            f"{fun['submitted']} submitted | "
            f"{fun['verified']} verified | "
            f"{fun['rejected']} rejected | "
            f"{fun['failed']} failed"
        )
        console.print(
            f"[bold cyan]Response rate:[/bold cyan] "
            f"{self.analytics.response_rate():.0%} "
            f"(avg rejection latency "
            f"{self.analytics.rejection_latency_days()['avg_days']} days)"
        )

    def render_html(self, limit: int = 1000) -> str:
        template = self._env.get_template("dashboard.html.j2")
        data = self.analytics.summary()
        data["recent"] = self.analytics.recent(limit=limit)
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return template.render(generated=generated, **data)

    def render_html_file(self, out_path: Path, limit: int = 1000) -> Path:
        html = self.render_html(limit=limit)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        return out_path
