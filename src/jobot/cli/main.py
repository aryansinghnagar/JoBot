import asyncio
import csv
from datetime import datetime
import json
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from jobot.adapters import (
    AdapterRegistry,
    GreenhouseAdapter,
    IndeedAdapter,
    LeverAdapter,
    LinkedInAdapter,
    MockATSAdapter,
    NaukriAdapter,
    SiteAdapter,
)
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.gui.sidecar import StdioSidecarServer
from jobot.models.domain import ApplicationStatus, CompensationDetails, PersonalInfo, UserProfile
from jobot.obs.manual_test_logger import ManualTestLogger
from jobot.runner import ContinuousCampaignRunner
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault

app = typer.Typer(name="jobot", help="Autonomous Job Application Operating System CLI")
console = Console()
test_logger = ManualTestLogger()


def get_adapter(site: str) -> SiteAdapter:
    return AdapterRegistry.get_adapter(site)


@app.command("setup")
def setup() -> None:
    """Run initial setup wizard and system diagnostics."""
    console.print("[bold green][OK] Running jobot Setup Wizard...[/bold green]")
    db = DatabaseManager()
    vault = CredentialVault()
    console.print(f"[green][OK] Database initialized at:[blue] {db.db_path}[/blue][/green]")
    console.print(f"[green][OK] Master vault initialized at:[blue] {vault.key_dir}[/blue][/green]")
    console.print("[bold blue][OK] Setup complete! Add your profile with 'jobot profile init'[/bold blue]")


@app.command("sidecar")
def sidecar_cmd() -> None:
    """Run stdio JSON-RPC sidecar protocol server for desktop GUI (Tauri 2.x)."""
    server = StdioSidecarServer()
    server.run_loop()


@app.command("profile")
def profile_cmd(
    action: str = typer.Argument("show", help="Action: 'show', 'init'"),
    first_name: str = typer.Option("", "--first-name", help="Candidate First Name"),
    last_name: str = typer.Option("", "--last-name", help="Candidate Last Name"),
    email: str = typer.Option("", "--email", help="Candidate Email"),
    phone: str = typer.Option("", "--phone", help="Candidate Phone"),
) -> None:
    """Manage candidate profile and vault encryption."""
    vault = CredentialVault()
    profile_dir = Path.home() / ".jobot" / "profiles"
    profile_path = profile_dir / "default.enc"

    if action == "init":
        p = UserProfile(
            profile_id="default",
            personal_info=PersonalInfo(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                location_city="Bangalore",
                location_state="Karnataka",
                location_country="India",
            ),
            compensation=CompensationDetails(
                current_ctc_inr=1200000,
                expected_ctc_inr=1800000,
                notice_period_days=30,
            ),
            skills=["Python", "FastAPI", "SQLite", "Playwright"],
        )
        saved_path = vault.save_encrypted_profile(p, profile_path)
        console.print(f"[bold green][OK] Profile encrypted & saved to:[blue] {saved_path}[/blue][/bold green]")
    else:
        if not profile_path.exists():
            console.print("[yellow]No profile found. Run 'jobot profile init' first.[/yellow]")
            return
        p = vault.load_encrypted_profile(profile_path)
        console.print(f"[bold cyan]Candidate Profile ({p.profile_id}):[/bold cyan]")
        console.print(f"Name: {p.personal_info.first_name} {p.personal_info.last_name}")
        console.print(f"Email: {p.personal_info.email}")
        console.print(f"Phone: {p.personal_info.phone}")
        console.print(f"Notice Period: {p.compensation.notice_period_days} Days")
        console.print(f"Skills: {', '.join(p.skills)}")


@app.command("continuous-campaign")
def continuous_campaign_cmd(
    goal: int = typer.Option(1000, "--goal", help="Target total applications goal (default: 1000)"),
    min_match: float = typer.Option(0.20, "--min-match", help="Minimum match score threshold (default: 0.20 for 20%)"),
) -> None:
    """Run continuous round-robin campaign across 15 portals maintaining log.md at project root."""
    runner = ContinuousCampaignRunner()
    asyncio.run(runner.run_continuous_campaign(goal_count=goal, min_match=min_match))


@app.command("auto-apply")
def auto_apply_cmd(
    target_title: str = typer.Option("Python Developer", "--title", help="Target job title to discover"),
    portals: str = typer.Option("naukri,linkedin,indeed,greenhouse,lever", "--portals", help="Comma-separated portal list"),
    auto_submit: bool = typer.Option(False, "--auto-submit", help="Bypass human final OK gate (Full Autonomous mode)"),
) -> None:
    """Automatically discover matching jobs across portals and prompt for final submission approval."""
    console.print(f"[bold cyan]jobot Discovery Engine: Searching for '{target_title}' across portals [{portals}]...[/bold cyan]")
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"

    if not profile_path.exists():
        console.print("[bold red][ERROR] Candidate profile missing.[/bold red]")
        console.print("[yellow]Please initialize your candidate profile first using: [bold blue]jobot profile init[/bold blue][/yellow]")
        raise typer.Exit(code=1)
    p = vault.load_encrypted_profile(profile_path)

    portal_list = [pt.strip() for pt in portals.split(",") if pt.strip()]
    discovery = JobDiscoveryEngine(active_portals=portal_list)

    matched_results = asyncio.run(discovery.discover_matching_jobs(p, target_title=target_title, limit_per_portal=1))

    console.print(f"[bold green]Discovered {len(matched_results)} matching positions![/bold green]\n")

    for idx, match in enumerate(matched_results, start=1):
        job = match.posting
        console.print(f"[bold yellow]Job {idx}/{len(matched_results)}: {job.title} at {job.company} ({job.site.upper()})[/bold yellow]")
        console.print(f"Match Score: [green]{int(match.match_score * 100)}% ({match.recommendation})[/green]")
        console.print(f"Matching Skills: {', '.join(match.matching_skills)}")
        console.print(f"URL: {job.url}")

        adapter = get_adapter(job.site)
        pipeline = ApplicationSubmissionPipeline(adapter, db)

        if auto_submit:
            # Full Autonomous mode
            app_res = asyncio.run(pipeline.execute(job.url, p, auto_approve=True))
            console.print(f"[bold green]Status: {app_res.status.value.upper()}[/bold green]\n")
        else:
            # Human-in-the-Loop Mode: Autonomous form fill, but prompts user for final submission OK!
            console.print("[cyan]Autonomously parsing job and filling form...[/cyan]")
            app_res = asyncio.run(pipeline.execute(job.url, p, auto_approve=False))

            if app_res.status == ApplicationStatus.PENDING_APPROVAL:
                console.print("\n[bold magenta]=== PRE-SUBMISSION VERIFICATION SUMMARY ===[/bold magenta]")
                console.print(f"Applicant: {p.personal_info.first_name} {p.personal_info.last_name} ({p.personal_info.email})")
                console.print(f"Target: {job.title} at {job.company}")
                if app_res.form_values:
                    console.print("Form Values to be submitted:")
                    for k, v in app_res.form_values.items():
                        console.print(f"  - {k}: {v}")

                user_approved = Confirm.ask(f"[bold green]Proceed with final submission to {job.company}?[/bold green]")
                if user_approved:
                    asyncio.run(pipeline.submit_and_verify(app_res))
                    if app_res.status == ApplicationStatus.VERIFIED:
                        console.print(f"[bold green][OK] Application SUBMITTED & VERIFIED for {job.company}![/bold green]\n")
                    else:
                        console.print(f"[bold red][ERROR] Submission failed: {app_res.error_message}[/bold red]\n")
                else:
                    app_res.status = ApplicationStatus.CANCELLED
                    db.save_application(app_res)
                    console.print("[yellow]Submission skipped by user.[/yellow]\n")


@app.command("run")
def run_cmd(
    job_url: str = typer.Argument(..., help="Job posting URL"),
    site: str = typer.Option("naukri", "--site", help="Site adapter: naukri, linkedin, indeed, greenhouse, lever, mock_ats"),
    approve: bool = typer.Option(False, "--approve", help="Auto-approve submission (autonomous mode)"),
) -> None:
    """Run application submission pipeline for a single job posting URL."""
    console.print(f"[bold cyan]jobot: Applying to job posting at {job_url} on site '{site}'[/bold cyan]")
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"

    if not profile_path.exists():
        console.print("[bold red][ERROR] Candidate profile missing.[/bold red]")
        console.print("[yellow]Please initialize your candidate profile first using: [bold blue]jobot profile init[/bold blue][/yellow]")
        raise typer.Exit(code=1)
    p = vault.load_encrypted_profile(profile_path)

    try:
        adapter = get_adapter(site)
        pipeline = ApplicationSubmissionPipeline(adapter, db)
        app_result = asyncio.run(pipeline.execute(job_url, p, auto_approve=approve))

        console.print(f"[bold green]Pipeline Status:[blue] {app_result.status.value.upper()}[/blue][/bold green]")
        if app_result.form_values:
            console.print("[cyan]Filled Form Values:[/cyan]")
            for k, v in app_result.form_values.items():
                console.print(f"  [OK] {k}: {v}")
    except Exception as exc:
        console.print(f"[bold red][ERROR] Pipeline failed: {exc}[/bold red]")
        issue = test_logger.log_issue(
            summary=f"Manual test pipeline execution failed on {site}",
            issue_type="ERROR",
            details=str(exc),
            site=site,
            exc=exc,
        )
        console.print(f"[yellow]Issue automatically logged for review: {issue.issue_id}[/yellow]")


@app.command("report-issue")
def report_issue_cmd(
    summary: str = typer.Argument(..., help="Brief summary of issue or vulnerability observed"),
    issue_type: str = typer.Option("USER_REPORT", "--type", help="Type: USER_REPORT, VULNERABILITY, DOM_DRIFT, ERROR"),
    site: Optional[str] = typer.Option(None, "--site", help="Target site (e.g. linkedin, naukri)"),
    details: str = typer.Option("", "--details", help="Additional details or repro notes"),
) -> None:
    """Log an issue, bug, or security vulnerability detected during manual testing."""
    issue = test_logger.log_issue(
        summary=summary,
        issue_type=issue_type,
        details=details,
        site=site,
    )
    console.print(f"[bold green][OK] Manual test issue logged: [blue]{issue.issue_id}[/blue][/bold green]")
    console.print(f"Logged to: {test_logger.markdown_report}")


@app.command("test-logs")
def test_logs_cmd() -> None:
    """View log of issues, vulnerabilities, and errors recorded during manual testing."""
    issues = test_logger.list_issues()
    if not issues:
        console.print("[yellow]No manual testing issues recorded yet.[/yellow]")
        return

    table = Table(title=f"Manual Testing Issue Log ({len(issues)} recorded)")
    table.add_column("Issue ID", style="dim")
    table.add_column("Type", style="bold red")
    table.add_column("Site")
    table.add_column("Summary")
    table.add_column("Timestamp")

    for iss in issues:
        table.add_row(
            iss.issue_id,
            iss.issue_type,
            iss.site or "N/A",
            iss.summary,
            iss.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command("status")
def status_cmd() -> None:
    """Show application tracking status history."""
    db = DatabaseManager()
    apps = db.list_applications(limit=20)

    table = Table(title="Application History & Status")
    table.add_column("App ID", style="dim")
    table.add_column("Site")
    table.add_column("Status", style="bold green")
    table.add_column("Trust Level")
    table.add_column("Created At")

    for a in apps:
        table.add_row(
            a.application_id[:8],
            a.site,
            a.status.value,
            a.trust_level.value,
            a.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@app.command("pause")
def pause_cmd() -> None:
    """Pause active background operations and save execution state."""
    state_path = Path.home() / ".jobot" / "runner_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"status": "PAUSED", "paused_at": datetime.now().isoformat()}), encoding="utf-8")
    console.print("[bold yellow][OK] All active automation loops paused. State saved to ~/.jobot/runner_state.json[/bold yellow]")


@app.command("resume")
def resume_cmd() -> None:
    """Resume paused background operations."""
    state_path = Path.home() / ".jobot" / "runner_state.json"
    if state_path.exists():
        state_path.write_text(json.dumps({"status": "RUNNING", "resumed_at": datetime.now().isoformat()}), encoding="utf-8")
    console.print("[bold green][OK] Automation loops resumed.[/bold green]")


import csv


@app.command("export")
def export_cmd(
    format_type: str = typer.Option("csv", "--format", help="Export format: csv or json"),
    output: Optional[str] = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Export application history to CSV or JSON."""
    db = DatabaseManager()
    apps = db.list_applications(limit=1000)

    if not output:
        output = f"applications_export.{format_type.lower()}"

    out_path = Path(output)

    if format_type.lower() == "json":
        data = [a.model_dump() for a in apps]
        out_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    else:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["application_id", "site", "job_id", "status", "trust_level", "created_at"])
            for a in apps:
                writer.writerow([a.application_id, a.site, a.job_id, a.status.value, a.trust_level.value, a.created_at])

    console.print(f"[bold green][OK] Exported {len(apps)} applications to {out_path.resolve()}[/bold green]")


from jobot.scheduler import SchedulerManager


@app.command("schedule")
def schedule_cmd(
    action: str = typer.Argument("list", help="Action: 'list', 'add', 'remove'"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression (e.g. '0 9 * * 1-5')"),
    command: Optional[str] = typer.Option(None, "--command", help="Command to execute"),
    schedule_id: Optional[str] = typer.Option(None, "--id", help="Schedule ID to remove"),
) -> None:
    """Manage cron-like automated application schedules."""
    sm = SchedulerManager()

    if action == "add":
        if not cron or not command:
            console.print("[bold red]Please specify --cron and --command for add action.[/bold red]")
            return
        entry = sm.add_schedule(cron, command)
        console.print(f"[bold green][OK] Schedule added: {entry['schedule_id']} ({cron}) -> {command}[/bold green]")
    elif action == "remove":
        if not schedule_id:
            console.print("[bold red]Please specify --id to remove.[/bold red]")
            return
        success = sm.remove_schedule(schedule_id)
        if success:
            console.print(f"[bold green][OK] Schedule '{schedule_id}' removed.[/bold green]")
        else:
            console.print(f"[yellow]Schedule '{schedule_id}' not found.[/yellow]")
    else:
        schedules = sm.list_schedules()
        if not schedules:
            console.print("[yellow]No background schedules configured.[/yellow]")
            return
        table = Table(title="Configured Jobot Schedules")
        table.add_column("Schedule ID", style="cyan")
        table.add_column("Cron", style="bold yellow")
        table.add_column("Command", style="green")
        for s in schedules:
            table.add_row(s.get("schedule_id"), s.get("cron"), s.get("command"))
        console.print(table)


from jobot.obs.tracing import TraceLogger


@app.command("traces")
def traces_cmd(
    action: str = typer.Argument("list", help="Action: 'list', 'show'"),
    run_id: Optional[str] = typer.Argument(None, help="Run ID for 'show' action"),
) -> None:
    """List or inspect OpenTelemetry-compatible trace spans."""
    tl = TraceLogger()
    if action == "list":
        trace_files = tl.list_traces()
        if not trace_files:
            console.print("[yellow]No trace files found in ~/.jobot/traces/[/yellow]")
            return
        table = Table(title="JoBot Trace Runs")
        table.add_column("Run ID", style="cyan")
        table.add_column("File Size", style="dim")
        for tf in trace_files:
            table.add_row(tf.stem, f"{tf.stat().st_size} bytes")
        console.print(table)
    elif action == "show":
        if not run_id:
            console.print("[bold red]Please provide run_id to show (e.g. jobot traces show <run_id>)[/bold red]")
            return
        spans = tl.get_trace_spans(run_id)
        if not spans:
            console.print(f"[yellow]No trace spans found for run_id '{run_id}'[/yellow]")
            return
        table = Table(title=f"Trace Timeline: {run_id}")
        table.add_column("Span Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Duration (ms)", style="magenta")
        table.add_column("Start Time", style="dim")
        for s in spans:
            table.add_row(
                s.get("name", ""),
                s.get("attributes", {}).get("status", "ok"),
                str(s.get("duration_ms", 0)),
                s.get("start_time", "")[:19],
            )
        console.print(table)


from jobot.obs.alerts import AlertDispatcher


@app.command("alerts")
def alerts_cmd(
    show_all: bool = typer.Option(False, "--all", help="Show all alerts including acknowledged"),
    ack_id: Optional[str] = typer.Option(None, "--ack", help="Acknowledge alert ID"),
) -> None:
    """List operational alerts or acknowledge an alert by ID."""
    dispatcher = AlertDispatcher()
    if ack_id:
        success = dispatcher.acknowledge_alert(ack_id)
        if success:
            console.print(f"[bold green][OK] Alert '{ack_id}' acknowledged.[/bold green]")
        else:
            console.print(f"[bold red][ERROR] Alert '{ack_id}' not found.[/bold red]")
        return

    alerts = dispatcher.list_alerts(unack_only=not show_all)
    if not alerts:
        console.print("[green]No unacknowledged system alerts.[/green]")
        return

    table = Table(title="JoBot Operational Alerts")
    table.add_column("Alert ID", style="cyan")
    table.add_column("Level", style="bold red")
    table.add_column("Title", style="bold yellow")
    table.add_column("Message")
    table.add_column("Timestamp", style="dim")
    table.add_column("Ack", style="green")

    for a in alerts:
        lvl = a.get("level", "INFO")
        style = "bold red" if lvl in ["CRITICAL", "HIGH"] else "yellow"
        table.add_row(
            a.get("alert_id", "")[:12],
            f"[{style}]{lvl}[/{style}]",
            a.get("title", ""),
            a.get("message", ""),
            a.get("timestamp", "")[:19],
            "Yes" if a.get("acknowledged") else "No",
        )

    console.print(table)


from jobot.evals.harness import EvalHarness


@app.command("evals")
def evals_cmd(
    action: str = typer.Argument("run", help="Action: 'run'"),
) -> None:
    """Run automated evaluation suite across 6 categories."""
    harness = EvalHarness()
    res = harness.run_eval_suite()

    console.print(f"\n[bold cyan]=== JoBot Continuous Evaluation Results ===[/bold cyan]")
    console.print(f"Scenarios Evaluated: [bold]{res['total']}[/bold]")
    console.print(f"Scenarios Passed:    [bold green]{res['passed']}[/bold green]")
    console.print(f"Overall Pass Rate:   [bold yellow]{int(res['pass_rate']*100)}%[/bold yellow]\n")

    table = Table(title="Category Breakdown")
    table.add_column("Category", style="cyan")
    table.add_column("Passed / Total", style="green")

    for cat, scores in res.get("category_scores", {}).items():
        table.add_row(cat, f"{scores['passed']} / {scores['total']}")

    console.print(table)


import shutil
from jobot.adapters.naukri.login import NaukriLoginFlow
from jobot.stealth.browser import BrowserSession


@app.command("login")
def login_cmd(
    portal: Optional[str] = typer.Argument(None, help="Target portal: naukri, linkedin, indeed, etc."),
    status: bool = typer.Option(False, "--status", help="Show active portal login sessions"),
    logout: Optional[str] = typer.Option(None, "--logout", help="Clear session for specified portal"),
) -> None:
    """Manage interactive portal login sessions and cookie persistence."""
    sessions_base = Path.home() / ".jobot" / "sessions"

    if status:
        if not sessions_base.exists():
            console.print("[yellow]No active portal sessions found.[/yellow]")
            return

        table = Table(title="Active Portal Login Sessions")
        table.add_column("Portal", style="cyan")
        table.add_column("Session Directory")
        table.add_column("Status", style="green")

        for p_dir in sessions_base.iterdir():
            if p_dir.is_dir():
                table.add_row(p_dir.name, str(p_dir), "ACTIVE")

        console.print(table)
        return

    if logout:
        target_dir = sessions_base / logout.lower().strip()
        if target_dir.exists():
            shutil.rmtree(target_dir)
            console.print(f"[bold green][OK] Session cleared for portal '{logout}'.[/bold green]")
        else:
            console.print(f"[yellow]No session found for portal '{logout}'.[/yellow]")
        return

    if not portal:
        console.print("[bold red][ERROR] Please specify portal name, --status, or --logout <portal>[/bold red]")
        console.print("[yellow]Usage: jobot login naukri[/yellow]")
        raise typer.Exit(code=1)

    portal_clean = portal.lower().strip()
    console.print(f"[bold cyan]Opening browser login for portal '{portal_clean}'...[/bold cyan]")

    if portal_clean == "naukri":
        flow = NaukriLoginFlow(headless=False)
        success = asyncio.run(flow.execute_login())
        if success:
            console.print(f"[bold green][OK] Naukri session successfully saved to {sessions_base / 'naukri'}[/bold green]")
    else:
        session = BrowserSession(portal=portal_clean, headless=False)
        asyncio.run(session.start())
        console.print(f"[bold green][OK] Browser launched. Complete login in browser window.[/bold green]")


if __name__ == "__main__":
    app()
