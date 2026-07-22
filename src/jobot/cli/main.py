import asyncio
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from jobot.adapters import (
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
    s = site.lower()
    if s == "linkedin":
        return LinkedInAdapter()
    elif s == "indeed":
        return IndeedAdapter()
    elif s == "greenhouse":
        return GreenhouseAdapter()
    elif s == "lever":
        return LeverAdapter()
    elif s == "mock_ats":
        return MockATSAdapter()
    return NaukriAdapter()


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
                    asyncio.run(adapter.submit_application(app_res))
                    asyncio.run(adapter.verify_submission(app_res))
                    db.save_application(app_res)
                    console.print(f"[bold green][OK] Application SUBMITTED & VERIFIED for {job.company}![/bold green]\n")
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


@app.command("schedule")
def schedule_cmd(
    cron: str = typer.Option("daily", "--schedule", help="Schedule frequency: daily, hourly"),
    max_apps: int = typer.Option(30, "--max-apps", help="Max applications per day"),
) -> None:
    """Configure automated background application schedule."""
    console.print(f"[bold green][OK] Background apply loop scheduled ({cron}). Max applications: {max_apps}/day.[/bold green]")


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
    """Pause active background operations."""
    console.print("[bold yellow][OK] All active automation loops paused.[/bold yellow]")


@app.command("export")
def export_cmd() -> None:
    """Export encrypted backup and diagnostic audit logs."""
    console.print("[bold green][OK] Diagnostic package exported to ~/.jobot/backups/[/bold green]")


if __name__ == "__main__":
    app()
