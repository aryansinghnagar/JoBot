import asyncio
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional
import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from jobot.adapters import AdapterRegistry, SiteAdapter, infer_site
from jobot.adapters.naukri.login import NaukriLoginFlow
from jobot.ai.qa_engine import QAEngine
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.config.manager import ConfigManager
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.documents import (
    AtsScorer,
    CoverLetterGenerator,
    DocumentTailor,
    ResumeExporter,
    TEMPLATE_NAMES,
    list_tones,
    pdftotext_available,
    tex_engine_available,
)
from jobot.evals.harness import EvalHarness
from jobot.gui.sidecar import StdioSidecarServer
from jobot.models.domain import ApplicationStatus, CompensationDetails, PersonalInfo, UserProfile
from jobot.obs.alerts import AlertDispatcher
from jobot.obs.manual_test_logger import ManualTestLogger
from jobot.obs.tracing import TraceLogger
from jobot.runner import ContinuousCampaignRunner
from jobot.scheduler import SchedulerManager
from jobot.stealth.browser import BrowserSession
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault
from jobot.tracker.analytics import TrackerAnalytics
from jobot.tracker.render import TrackerRenderer
from jobot.digest.generator import DigestGenerator
from jobot.notify.email import EmailSender

app = typer.Typer(name="jobot", help="Autonomous Job Application Operating System CLI")
console = Console()
err_console = Console(stderr=True)
test_logger = ManualTestLogger()


def get_adapter(site: str) -> SiteAdapter:
    return AdapterRegistry.get_adapter(site)


def _resolve_job(
    job_id: Optional[str],
    url: Optional[str],
    site: Optional[str],
    db: DatabaseManager,
    out_console: Console,
) -> Any:
    """Resolve a JobPosting from a saved job id or a URL (live parse)."""

    if job_id:
        job = db.get_job_posting(job_id)
        if job is None:
            out_console.print(
                f"[bold red][ERROR] No saved posting with job id '{job_id}'.[/bold red]"
            )
            out_console.print(
                "[yellow]Save postings first: [bold blue]jobot scrape <board> --save[/bold blue][/yellow]"
            )
            return None
        return job
    if url:
        try:
            site_name = site or infer_site(url)
        except ValueError as exc:
            out_console.print(f"[bold red][ERROR] {exc}[/bold red]")
            out_console.print(
                "[yellow]Run [bold blue]jobot list-sites[/bold blue] to see supported sites, "
                "or pass [bold blue]--site[/bold blue] explicitly.[/yellow]"
            )
            return None
        adapter = get_adapter(site_name)
        job = asyncio.run(adapter.parse_job_posting(url))
        if not job.title or not job.job_id:
            out_console.print("[bold red][ERROR] Could not parse job posting from URL.[/bold red]")
            return None
        return job
    out_console.print("[bold red][ERROR] Provide --job-id or --url.[/bold red]")
    return None


@app.command("list-sites")
def list_sites() -> None:
    """List all registered job-site adapters and their capability tiers."""
    from jobot.adapters.capabilities import AdapterCapability

    table = Table(title="Supported Job Portals & ATS Adapters")
    table.add_column("Portal / Site", style="cyan bold")
    table.add_column("Capability Tier", style="bold")
    table.add_column("Apply Supported", justify="center")
    table.add_column("Mechanism", style="dim")

    for site_name, caps in AdapterRegistry.list_supported_sites_with_capabilities():
        can_submit = bool(caps & (AdapterCapability.SUBMIT_API | AdapterCapability.SUBMIT_BROWSER))
        if caps & AdapterCapability.SUBMIT_API:
            tier = "[green]Real API[/green]"
            mech = "Direct HTTP POST API"
        elif caps & AdapterCapability.SUBMIT_BROWSER:
            tier = "[yellow]Live Browser[/yellow]"
            mech = "Patchright (JOBOT_RUN_LIVE_BROWSER=1)"
        elif caps & AdapterCapability.PARSE:
            tier = "[blue]Discovery + Parse[/blue]"
            mech = "Public JSON API / Scraper"
        else:
            tier = "[dim]Discovery Only[/dim]"
            mech = "Scraper Engine (JobSpy)"

        apply_badge = "[green]Yes[/green]" if can_submit else "[dim]No[/dim]"
        table.add_row(site_name, tier, apply_badge, mech)

    console.print(table)


@app.command("site-health")
def site_health_cmd() -> None:
    """Display real-time health and availability metrics for all supported job portals and ATS adapters (UC-13)."""
    from jobot.stealth.site_health import SiteHealthMonitor

    monitor = SiteHealthMonitor()
    table = Table(title="JoBot Portal & ATS Site Health")
    table.add_column("Portal", style="cyan bold")
    table.add_column("Status", style="bold")
    table.add_column("Total Requests", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Consecutive Fails", justify="right")
    table.add_column("Last Error", style="dim")

    for site in AdapterRegistry.list_supported_sites():
        st = monitor.get_status(site)
        status_color = (
            "green" if st.status == "HEALTHY" else ("yellow" if st.status == "DEGRADED" else "red")
        )
        table.add_row(
            site,
            f"[{status_color}]{st.status}[/{status_color}]",
            str(st.total_requests),
            f"{st.success_rate * 100:.1f}%",
            str(st.consecutive_failures),
            st.last_error or "None",
        )

    console.print(table)


@app.command("setup")
def setup() -> None:
    """Run initial setup wizard and system diagnostics."""
    console.print("[bold green][OK] Running jobot Setup Wizard...[/bold green]")
    db = DatabaseManager()
    vault = CredentialVault()
    console.print(f"[green][OK] Database initialized at:[blue] {db.db_path}[/blue][/green]")
    console.print(f"[green][OK] Master vault initialized at:[blue] {vault.key_dir}[/blue][/green]")
    console.print(
        "[bold blue][OK] Setup complete! Add your profile with 'jobot profile init'[/bold blue]"
    )


db_app = typer.Typer(help="Database migration operations (UC-07).")
task_app = typer.Typer(help="Durable task queue inspection (UC-01).")
approval_app = typer.Typer(help="Approval request management (UC-05).")
app.add_typer(db_app, name="db")
app.add_typer(task_app, name="task")
app.add_typer(approval_app, name="approval")


@db_app.command("status")
def db_status() -> None:
    """Show applied and pending schema migrations."""
    from jobot.storage.migrations import migration_status

    db = DatabaseManager()
    with db._get_connection() as conn:  # noqa: SLF001 - CLI is a trusted internal caller
        status = migration_status(conn)
    for mig in status["migrations"]:
        state = "[green]applied[/green]" if mig["applied"] else "[yellow]pending[/yellow]"
        console.print(f"  v{mig['version']} {mig['name']}: {state} ({mig['checksum']}…)")
    if status["pending"]:
        console.print("[yellow]Run `jobot db migrate` to apply pending migrations.[/yellow]")


@db_app.command("migrate")
def db_migrate() -> None:
    """Apply pending schema migrations."""
    from jobot.storage.migrations import run_migrations

    db = DatabaseManager()  # __init__ runs migrations already; re-run for explicitness
    with db._get_connection() as conn:  # noqa: SLF001 - CLI is a trusted internal caller
        applied = run_migrations(conn)
    if applied:
        console.print(f"[green]Applied migrations: {applied}[/green]")
    else:
        console.print("[green]Database is up to date.[/green]")


@db_app.command("backup")
def db_backup(
    out: Optional[str] = typer.Option(None, "--out", help="Output path for backup database file"),
) -> None:
    """Create a hot backup of the SQLite database (UC-44)."""
    db = DatabaseManager()
    target = Path(out) if out else None
    backup_path = db.backup(target)
    console.print(
        f"[bold green][OK] Database backed up to: [blue]{backup_path}[/blue][/bold green]"
    )


@db_app.command("restore")
def db_restore(
    source: str = typer.Argument(..., help="Path to backup database file"),
) -> None:
    """Restore SQLite database from a backup file (UC-44)."""
    db = DatabaseManager()
    src_path = Path(source)
    if not src_path.exists():
        console.print(f"[bold red]Backup file does not exist: {src_path}[/bold red]")
        raise typer.Exit(1)
    db.restore(src_path)
    console.print(
        f"[bold green][OK] Database restored successfully from: [blue]{src_path}[/blue][/bold green]"
    )


@task_app.command("list")
def task_list(status: Optional[str] = None) -> None:
    """List durable tasks, optionally filtered by status."""
    from jobot.execution.engine import DurableTaskEngine, TaskStatus

    engine = DurableTaskEngine(DatabaseManager())
    wanted = TaskStatus(status.upper()) if status else None
    tasks = engine.list_tasks(wanted)
    if not tasks:
        console.print("[yellow]No tasks.[/yellow]")
        return
    for t in tasks:
        console.print(
            f"  {t.id} [{t.status.value}] pri={t.priority} attempts={t.attempts}/"
            f"{t.max_attempts} owner={t.owner or '-'} :: {t.description[:60]}"
        )


@approval_app.command("list")
def approval_list(status: str = "PENDING") -> None:
    """List approval requests (default: pending)."""
    from jobot.execution.engine import ApprovalStatus, DurableTaskEngine

    engine = DurableTaskEngine(DatabaseManager())
    for a in engine.list_approvals(ApprovalStatus(status.upper())):
        console.print(
            f"  {a.id} [{a.status.value}] {a.action_type} risk=R{a.risk_level} "
            f"task={a.task_id} requested_by={a.requested_by}"
        )


@approval_app.command("decide")
def approval_decide(approval_id: str, decision: str, reason: str = "") -> None:
    """Decide an approval: APPROVE | DENY | DEFER."""
    from jobot.execution.engine import ApprovalStatus, DurableTaskEngine, EngineError

    mapping = {
        "APPROVE": ApprovalStatus.APPROVED,
        "DENY": ApprovalStatus.DENIED,
        "DEFER": ApprovalStatus.DEFERRED,
    }
    normalized = mapping.get(decision.upper())
    if normalized is None:
        console.print("[bold red]decision must be APPROVE, DENY, or DEFER[/bold red]")
        raise typer.Exit(code=2)
    engine = DurableTaskEngine(DatabaseManager())
    try:
        rec = engine.decide_approval(approval_id, normalized, decided_by="cli-user", reason=reason)
    except EngineError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]{rec.id} -> {rec.status.value}[/green]")


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
        console.print(
            f"[bold green][OK] Profile encrypted & saved to:[blue] {saved_path}[/blue][/bold green]"
        )
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


@app.command("import-resume")
def import_resume_cmd(
    resume_file: str = typer.Argument(..., help="Path to resume file (PDF or text)"),
    profile_id: str = typer.Option("default", "--profile-id", help="Profile ID to update"),
    save_profile: bool = typer.Option(
        True, "--save/--no-save", help="Save extracted profile to encrypted vault"
    ),
) -> None:
    """Ingest a resume file, construct candidate UserProfile, and seed CandidateTruthStore (UC-25)."""
    from jobot.documents.importer import ResumeImporter

    importer = ResumeImporter()
    path = Path(resume_file)
    if not path.exists():
        console.print(f"[bold red]Resume file not found: {path}[/bold red]")
        raise typer.Exit(1)

    console.print(f"[cyan]Ingesting resume from [bold]{path.name}[/bold]...[/cyan]")
    profile, fact_count = asyncio.run(importer.import_and_seed(path, profile_id=profile_id))

    if save_profile:
        vault = CredentialVault()
        profile_dir = Path.home() / ".jobot" / "profiles"
        profile_path = profile_dir / f"{profile_id}.enc"
        vault.save_encrypted_profile(profile, profile_path)
        console.print(f"[green]Encrypted profile saved to {profile_path}[/green]")

    console.print(
        f"[bold green][OK] Ingested candidate profile ({profile.personal_info.first_name} {profile.personal_info.last_name}) "
        f"and seeded {fact_count} ground truth facts into candidate_facts![/bold green]"
    )
    console.print(f"Skills: {', '.join(profile.skills[:10])}")


@app.command("continuous-campaign")
def continuous_campaign_cmd(
    goal: int = typer.Option(1000, "--goal", help="Target total applications goal (default: 1000)"),
    min_match: float = typer.Option(
        0.20, "--min-match", help="Minimum match score threshold (default: 0.20 for 20%)"
    ),
    auto_submit: bool = typer.Option(
        True,
        "--auto-submit/--supervised",
        help="Run in autonomous submit mode or supervised approval mode",
    ),
) -> None:
    """Run continuous round-robin campaign across 15 portals maintaining log.md at project root."""
    runner = ContinuousCampaignRunner()
    asyncio.run(
        runner.run_continuous_campaign(
            goal_count=goal, min_match=min_match, auto_submit=auto_submit
        )
    )


@app.command("auto-apply")
def auto_apply_cmd(
    target_title: str = typer.Option(
        "Python Developer", "--title", help="Target job title to discover"
    ),
    portals: str = typer.Option(
        "naukri,linkedin,indeed,greenhouse,lever", "--portals", help="Comma-separated portal list"
    ),
    auto_submit: bool = typer.Option(
        False, "--auto-submit", help="Bypass human final OK gate (Full Autonomous mode)"
    ),
) -> None:
    """Automatically discover matching jobs across portals and prompt for final submission approval."""
    console.print(
        f"[bold cyan]jobot Discovery Engine: Searching for '{target_title}' across portals [{portals}]...[/bold cyan]"
    )
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"

    if not profile_path.exists():
        console.print("[bold red][ERROR] Candidate profile missing.[/bold red]")
        console.print(
            "[yellow]Please initialize your candidate profile first using: [bold blue]jobot profile init[/bold blue][/yellow]"
        )
        raise typer.Exit(code=1)
    p = vault.load_encrypted_profile(profile_path)

    portal_list = [pt.strip() for pt in portals.split(",") if pt.strip()]
    discovery = JobDiscoveryEngine(active_portals=portal_list)

    matched_results = asyncio.run(
        discovery.discover_matching_jobs(p, target_title=target_title, limit_per_portal=1)
    )

    console.print(
        f"[bold green]Discovered {len(matched_results)} matching positions![/bold green]\n"
    )

    for idx, match in enumerate(matched_results, start=1):
        job = match.posting
        console.print(
            f"[bold yellow]Job {idx}/{len(matched_results)}: {job.title} at {job.company} ({job.site.upper()})[/bold yellow]"
        )
        console.print(
            f"Match Score: [green]{int(match.match_score * 100)}% ({match.recommendation})[/green]"
        )
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
                console.print(
                    "\n[bold magenta]=== PRE-SUBMISSION VERIFICATION SUMMARY ===[/bold magenta]"
                )
                console.print(
                    f"Applicant: {p.personal_info.first_name} {p.personal_info.last_name} ({p.personal_info.email})"
                )
                console.print(f"Target: {job.title} at {job.company}")
                if app_res.form_values:
                    console.print("Form Values to be submitted:")
                    for k, v in app_res.form_values.items():
                        console.print(f"  - {k}: {v}")

                user_approved = Confirm.ask(
                    f"[bold green]Proceed with final submission to {job.company}?[/bold green]"
                )
                if user_approved:
                    # Record the human decision on the durable approval so
                    # submit_and_verify's gate passes across restarts (G3).
                    approval_id = (app_res.form_values or {}).get("_approval_id")
                    if approval_id:
                        from jobot.execution.engine import ApprovalStatus as _AS
                        from jobot.execution.engine import DurableTaskEngine as _DTE

                        _DTE(db).decide_approval(
                            str(approval_id), _AS.APPROVED, decided_by="cli-human"
                        )
                    asyncio.run(pipeline.submit_and_verify(app_res))
                    final_status: ApplicationStatus = getattr(app_res, "status")
                    if final_status in (ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED):
                        console.print(
                            f"[bold green][OK] Application SUBMITTED & VERIFIED for {job.company}![/bold green]\n"
                        )
                    elif final_status == ApplicationStatus.SUBMISSION_UNKNOWN:
                        console.print(
                            "[bold yellow][!] Submission outcome UNKNOWN — reconciliation "
                            "will verify without re-submitting (jobot approval/tracker).[/bold yellow]\n"
                        )
                    else:
                        console.print(
                            f"[bold red][ERROR] Submission failed: {app_res.error_message}[/bold red]\n"
                        )
                else:
                    approval_id = (app_res.form_values or {}).get("_approval_id")
                    if approval_id:
                        from jobot.execution.engine import ApprovalStatus as _AS
                        from jobot.execution.engine import DurableTaskEngine as _DTE

                        _DTE(db).decide_approval(
                            str(approval_id),
                            _AS.DENIED,
                            decided_by="cli-human",
                            reason="denied interactively",
                        )
                    app_res.status = ApplicationStatus.CANCELLED
                    db.save_application(app_res)
                    console.print("[yellow]Submission skipped by user.[/yellow]\n")


@app.command("scrape")
def scrape_cmd(
    board: str = typer.Argument(
        ...,
        help="Board to scrape: linkedin, indeed, glassdoor, google, zip_recruiter, bayt, "
        "naukri, bdjobs, greenhouse, lever, ashby, smartrecruiters, careers, mock_ats — "
        "or 'all'.",
    ),
    keywords: str = typer.Option("", "--keywords", help="Search keywords (job boards)"),
    location: str = typer.Option("", "--location", help="Location filter (job boards)"),
    limit: int = typer.Option(25, "--limit", help="Max postings to fetch"),
    companies: str = typer.Option(
        "", "--companies", help="Comma-separated companies (ATS boards / careers)"
    ),
    all_boards: bool = typer.Option(
        False, "--all", help="Scrape every available board in sequence"
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit results as JSON to stdout"),
    no_dedup: bool = typer.Option(False, "--no-dedup", help="Disable the two-tier dedup"),
    hours_old: Optional[int] = typer.Option(
        72, "--hours-old", help="Only postings newer than N hours"
    ),
    country: str = typer.Option(
        "USA", "--country", help="Indeed country code (e.g. USA, GBR, IND)"
    ),
    save: bool = typer.Option(
        False, "--save", help="Persist unique postings to the job store (for 'jobot apply')"
    ),
) -> None:
    """Scrape real job postings from a board, dedup, and show stats."""
    from jobot.adapters.greenhouse import GreenhouseAdapter
    from jobot.scrapers import JobSpyNotInstalledError
    from jobot.scrapers.ats import FAMILY_ADAPTERS
    from jobot.scrapers.careers import CareerPageScanner
    from jobot.scrapers.dedup import DedupService
    from jobot.scrapers.jobspy import JOBS_BOARDS, JobSpyAdapter

    all_boards_list = list(JOBS_BOARDS) + [
        "greenhouse",
        "lever",
        "ashby",
        "smartrecruiters",
        "careers",
        "mock_ats",
    ]
    boards = all_boards_list if all_boards else [board.strip().lower()]
    if not all_boards:
        for b in boards:
            if b not in all_boards_list:
                console.print(
                    f"[bold red][ERROR] Unknown board '{b}'. Supported: {', '.join(all_boards_list)}[/bold red]"
                )
                raise typer.Exit(code=1)

    company_list = [c.strip() for c in companies.split(",") if c.strip()]
    config = ConfigManager()
    db = DatabaseManager()
    dedup = DedupService(db=db) if not no_dedup else None
    results: List[Dict[str, Any]] = []
    failures = 0

    def progress(msg: str) -> None:
        # Progress goes to stderr in JSON mode so stdout stays machine-readable.
        if json_out:
            err_console.print(msg)
        else:
            console.print(msg)

    for b in boards:
        try:
            if b in JOBS_BOARDS:
                delay = float(config.get("scraper.jobspy.delay_s", 1.0))
                proxies_raw = config.get("scraper.jobspy.proxy_list", "")
                proxies = [p.strip() for p in str(proxies_raw).split(",") if p.strip()]
                scraper = JobSpyAdapter(b, delay_s=delay, proxies=proxies or None)
                postings = asyncio.run(
                    scraper.discover_jobs(
                        keywords=keywords,
                        location=location,
                        limit=limit,
                        hours_old=hours_old,
                        country_indeed=country,
                    )
                )
            elif b in FAMILY_ADAPTERS:
                if not company_list:
                    progress(f"[yellow]Board '{b}' requires --companies; skipping[/yellow]")
                    continue
                adapter = FAMILY_ADAPTERS[b](company=company_list[0])
                postings = asyncio.run(adapter.discover_jobs(limit=limit))
            elif b == "greenhouse":
                if not company_list:
                    progress("[yellow]Board 'greenhouse' requires --companies; skipping[/yellow]")
                    continue
                adapter = GreenhouseAdapter()
                postings = asyncio.run(adapter.discover_jobs(company=company_list[0], limit=limit))
            elif b == "careers":
                scanner = CareerPageScanner(companies=company_list)
                postings = asyncio.run(scanner.discover_jobs(limit=limit))
            elif b == "mock_ats":
                from jobot.adapters.mock_ats import MockATSAdapter

                postings = asyncio.run(MockATSAdapter().discover_jobs(limit=limit))
            else:  # pragma: no cover
                postings = []

            if dedup is not None:
                filtered = dedup.filter_unique(postings)
                unique, rejected = filtered.unique, filtered.rejected
            else:
                unique, rejected = postings, 0
            if save:
                for p in unique:
                    db.save_job_posting(p)
            for p in unique:
                results.append(
                    {
                        "site": p.site,
                        "title": p.title,
                        "company": p.company,
                        "location": p.location,
                        "url": p.url,
                        "description": p.description,
                    }
                )
            progress(
                f"[bold cyan]{b}[/bold cyan]: scraped {len(postings)}, "
                f"kept {len(unique)}, duplicates {rejected}"
                + (" [green](saved)[/green]" if save else "")
            )
        except JobSpyNotInstalledError as exc:
            failures += 1
            progress(f"[bold yellow]{b}: {exc}[/bold yellow]")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            progress(f"[bold red]{b}: scrape failed: {exc}[/bold red]")

    if json_out:
        # Plain ASCII stdout (ensure_ascii) — immune to console encoding quirks.
        sys.stdout.write(json.dumps(results, indent=2, default=str) + "\n")
        return

    table = Table(title="Scraped Postings")
    for col in ("Site", "Title", "Company", "Location", "URL"):
        table.add_column(col, style="bold" if col == "Title" else "")
    for r in results:
        table.add_row(r["site"], r["title"], r["company"], r["location"], r["url"])
    console.print(table)
    total = len(results)
    console.print(
        f"[bold green]Total: {total} unique postings from {len(boards)} board(s), "
        f"{failures} failed[/bold green]"
    )
    if total == 0 and failures == len(boards):
        raise typer.Exit(code=1)


@app.command("dedup")
def dedup_cmd(
    stats: bool = typer.Option(True, "--stats", help="Show dedup cache stats"),
) -> None:
    """Show the persistent dedup cache state."""
    from jobot.scrapers.dedup import DedupService

    service = DedupService()
    entries = service.db.list_dedup_entries()
    console.print(f"[bold cyan]Dedup cache: {len(entries)} unique posting(s) recorded[/bold cyan]")
    if stats and entries:
        table = Table(title="Dedup Cache Sample")
        for col in ("Title", "Company", "Location"):
            table.add_column(col, style="bold" if col == "Title" else "")
        for e in entries[:10]:
            table.add_row(e["title"], e["company"], e["location"])
        console.print(table)


@app.command("run")
def run_cmd(
    job_url: str = typer.Argument(..., help="Job posting URL"),
    site: str = typer.Option(
        "naukri",
        "--site",
        help="Site adapter: naukri, linkedin, indeed, greenhouse, lever, mock_ats",
    ),
    approve: bool = typer.Option(
        False, "--approve", help="Auto-approve submission (autonomous mode)"
    ),
) -> None:
    """Run application submission pipeline for a single job posting URL."""
    console.print(
        f"[bold cyan]jobot: Applying to job posting at {job_url} on site '{site}'[/bold cyan]"
    )
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"

    if not profile_path.exists():
        console.print("[bold red][ERROR] Candidate profile missing.[/bold red]")
        console.print(
            "[yellow]Please initialize your candidate profile first using: [bold blue]jobot profile init[/bold blue][/yellow]"
        )
        raise typer.Exit(code=1)
    p = vault.load_encrypted_profile(profile_path)

    try:
        adapter = get_adapter(site)
        pipeline = ApplicationSubmissionPipeline(adapter, db)
        app_result = asyncio.run(pipeline.execute(job_url, p, auto_approve=approve))

        console.print(
            f"[bold green]Pipeline Status:[blue] {app_result.status.value.upper()}[/blue][/bold green]"
        )
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


@app.command("apply")
def apply_cmd(
    job_id: Optional[str] = typer.Argument(
        None,
        help="Saved job posting id (see 'jobot scrape --save'); or use --url",
    ),
    url: Optional[str] = typer.Option(None, "--url", help="Job posting URL to apply to"),
    site: Optional[str] = typer.Option(None, "--site", help="Site for --url (inferred if omitted)"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Tailor + generate resume PDF + cover letter + ATS score, WITHOUT submitting",
    ),
    resume_saga: Optional[str] = typer.Option(None, "--resume", help="Resume a saga by id"),
    approve: bool = typer.Option(False, "--approve", help="Auto-approve submission (autonomous)"),
    template: str = typer.Option(
        "default", "--template", help=f"Resume template: {', '.join(TEMPLATE_NAMES)}"
    ),
    tone: str = typer.Option(
        "classic", "--tone", help=f"Cover letter tone: {', '.join(list_tones())}"
    ),
    extra_prompt: str = typer.Option("", "--extra-prompt", help="Extra cover letter instructions"),
    engine: Optional[str] = typer.Option(None, "--engine", help="PDF engine: latex, fallback"),
) -> None:
    """Tailor documents and submit an application via the saga orchestrator."""
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing. Run 'jobot profile init'.[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    job = _resolve_job(job_id, url, site, db, console)
    if job is None:
        raise typer.Exit(code=1)

    orchestrator = ApplyOrchestrator(db)
    result = asyncio.run(
        orchestrator.apply(
            job,
            profile,
            auto_approve=approve,
            dry_run=dry_run,
            resume_saga_id=resume_saga,
            template=template,
            engine=engine,
            tone=tone,
            extra_prompt=extra_prompt,
        )
    )

    if result.artifacts:
        console.print("\n[bold magenta]=== GENERATED APPLICATION PACKAGE ===[/bold magenta]")
        console.print(f"Resume PDF:   [blue]{result.artifacts['resume_pdf']}[/blue]")
        console.print(f"Cover letter: [blue]{result.artifacts['cover_letter']}[/blue]")
        console.print(
            f"ATS score:    [yellow]{result.artifacts['ats_score']:.2f}[/yellow] "
            f"({'PASS' if result.artifacts['ats_passed'] else 'BELOW 0.85'})"
        )
        console.print(
            f"Truthful:     {'[green]yes[/green]' if result.artifacts['is_truthful'] else '[bold red]NO[/bold red]'}"
        )

    for note in result.notes:
        console.print(f"[yellow]  note: {note}[/yellow]")

    if dry_run:
        console.print(
            f"\n[bold cyan]Dry run complete (saga {result.saga_id[:8]}). "
            f"No submission performed.[/bold cyan]"
        )
        return

    if result.app_status == "PENDING_APPROVAL" and not approve:
        user_ok = Confirm.ask(
            f"[bold green]Review package above. Proceed with final submission to "
            f"{job.company}?[/bold green]"
        )
        if not user_ok:
            console.print("[yellow]Submission skipped by user.[/yellow]")
            return
        if not result.application_id:
            console.print("[bold red][ERROR] No application record to submit.[/bold red]")
            raise typer.Exit(code=1)
        app = db.get_application(result.application_id)
        if app is None:
            console.print("[bold red][ERROR] Application record not found in database.[/bold red]")
            raise typer.Exit(code=1)
        final = asyncio.run(orchestrator.submit_approved(app))
        console.print(
            f"[bold green][OK] Final status: {final.app_status}[/bold green]"
            + (f" — {final.notes[0]}" if final.notes else "")
        )
        return

    console.print(f"\n[bold cyan]Final status: {result.app_status}[/bold cyan]")
    console.print(
        f"Saga id: {result.saga_id}  (resume with 'jobot apply --resume {result.saga_id}')"
    )


@app.command("coverletter")
def coverletter_cmd(
    job_id: Optional[str] = typer.Argument(None, help="Saved job posting id; or use --url"),
    url: Optional[str] = typer.Option(None, "--url", help="Job posting URL"),
    site: Optional[str] = typer.Option(None, "--site", help="Site for --url (inferred if omitted)"),
    tone: str = typer.Option("classic", "--tone", help=f"Tone: {', '.join(list_tones())}"),
    extra_prompt: str = typer.Option("", "--extra-prompt", help="Extra instructions"),
    save: bool = typer.Option(False, "--save", help="Save letter to ~/.jobot/resumes/"),
) -> None:
    """Generate a profile-grounded cover letter for a job."""
    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing. Run 'jobot profile init'.[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    job = _resolve_job(job_id, url, site, db, console)
    if job is None:
        raise typer.Exit(code=1)

    generator = CoverLetterGenerator()
    matching = [s for s in job.parsed_skills if s.lower() in {ps.lower() for ps in profile.skills}]
    letter = asyncio.run(
        generator.generate(
            job, profile, matching_skills=matching or None, tone=tone, extra_prompt=extra_prompt
        )
    )
    console.print(letter)
    if save:
        out_dir = Path.home() / ".jobot" / "resumes"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"cover_{job.job_id}.txt"
        path.write_text(letter, encoding="utf-8")
        console.print(f"\n[bold green][OK] Saved to [blue]{path}[/blue][/bold green]")


@app.command("qa")
def qa_cmd(
    question: str = typer.Argument(..., help="Question to answer from profile facts"),
) -> None:
    """Answer a job application question using the profile-grounded QA engine."""
    vault = CredentialVault()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing. Run 'jobot profile init'.[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    engine = QAEngine()
    result = asyncio.run(engine.answer_question(question, profile))
    console.print(f"[bold cyan]Question type:[/bold cyan] {result.question_type.value}")
    console.print(f"[bold green]Answer:[/bold green] {result.answer}")
    console.print(
        f"Grounded: {'[green]yes[/green]' if result.is_grounded else '[red]no[/red]'} | "
        f"Confidence: {result.confidence_score}"
    )
    if result.requires_user_approval:
        console.print("[yellow]This answer requires your approval before submission.[/yellow]")


@app.command("report-issue")
def report_issue_cmd(
    summary: str = typer.Argument(..., help="Brief summary of issue or vulnerability observed"),
    issue_type: str = typer.Option(
        "USER_REPORT", "--type", help="Type: USER_REPORT, VULNERABILITY, DOM_DRIFT, ERROR"
    ),
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
    console.print(
        f"[bold green][OK] Manual test issue logged: [blue]{issue.issue_id}[/blue][/bold green]"
    )
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
    state_path.write_text(
        json.dumps({"status": "PAUSED", "paused_at": datetime.now().isoformat()}), encoding="utf-8"
    )
    console.print(
        "[bold yellow][OK] All active automation loops paused. State saved to ~/.jobot/runner_state.json[/bold yellow]"
    )


@app.command("resume")
def resume_cmd(
    action: str = typer.Argument(
        "runner",
        help="Action: 'runner' (resume paused loops), 'tailor', 'ats-check', 'templates'",
    ),
    job_id: Optional[str] = typer.Option(None, "--job-id", help="Saved job posting id (tailor)"),
    url: Optional[str] = typer.Option(None, "--url", help="Job posting URL (tailor)"),
    site: Optional[str] = typer.Option(None, "--site", help="Site for --url (inferred if omitted)"),
    template: str = typer.Option("default", "--template", help="Resume template name"),
    engine: Optional[str] = typer.Option(None, "--engine", help="PDF engine: latex, fallback"),
    pdf_file: Optional[str] = typer.Option(None, "--file", help="PDF file to ATS-check"),
    output: Optional[str] = typer.Option(None, "--output", help="Output directory for artifacts"),
) -> None:
    """Resume paused loops, or produce/check tailored resume documents."""
    if action == "runner":
        state_path = Path.home() / ".jobot" / "runner_state.json"
        if state_path.exists():
            state_path.write_text(
                json.dumps({"status": "RUNNING", "resumed_at": datetime.now().isoformat()}),
                encoding="utf-8",
            )
        console.print("[bold green][OK] Automation loops resumed.[/bold green]")
        return

    if action == "templates":
        table = Table(title="Resume Templates & PDF Engines")
        table.add_column("Name", style="cyan")
        table.add_column("Available", style="green")
        for name in TEMPLATE_NAMES:
            table.add_row(name, "yes")
        table.add_row("latex engine", "yes" if tex_engine_available() else "no (fallback used)")
        table.add_row("pdftotext", "yes" if pdftotext_available() else "no (pdfminer used)")
        console.print(table)
        return

    if action == "ats-check":
        target = Path(pdf_file) if pdf_file else (Path.home() / ".jobot" / "resumes")
        scorer = AtsScorer()
        if target.is_file():
            score = scorer.score_pdf(target)
            console.print(
                f"[bold cyan]ATS score for {target}: [yellow]{score.score:.2f}[/yellow] "
                f"({'PASS' if score.passed else 'FAIL'})[/bold cyan]"
            )
            for check, ok in score.details.get("passed_checks", {}).items():
                console.print(f"  - {check}: {'[green]PASS[/green]' if ok else '[red]FAIL[/red]'}")
        else:
            scores = []
            for pdf in sorted(target.glob("*.pdf")):
                score = scorer.score_pdf(pdf)
                scores.append((pdf, score))
                console.print(
                    f"{pdf.name}: [yellow]{score.score:.2f}[/yellow] "
                    f"({'PASS' if score.passed else 'FAIL'})"
                )
            if not scores:
                console.print("[yellow]No PDF resumes found to check.[/yellow]")
        return

    vault = CredentialVault()
    db = DatabaseManager()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing. Run 'jobot profile init'.[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    job = _resolve_job(job_id, url, site, db, console)
    if job is None:
        raise typer.Exit(code=1)

    if action == "tailor":
        tailor = DocumentTailor()
        tailored = asyncio.run(tailor.generate_tailored_materials(job, profile))
        exporter = ResumeExporter()
        out_dir = Path(output) if output else Path.home() / ".jobot" / "resumes"
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf, ats = exporter.export_resume_pdf(
            profile,
            template=template,
            engine=engine,
            output_dir=out_dir,
            summary=tailored.tailored_summary,
            skills=tailored.highlighted_skills or None,
            experience_bullets={
                f"{item.get('company', '')}|{item.get('title', '')}": [
                    str(b) for b in item.get("bullets", [])
                ]
                for item in tailored.tailored_experience
            },
        )
        cover_path = out_dir / f"cover_{job.job_id}.txt"
        cover_path.write_text(tailored.cover_letter_text, encoding="utf-8")
        console.print(
            f"[bold green][OK] Tailored resume: [blue]{pdf}[/blue][/bold green]\n"
            f"Cover letter: [blue]{cover_path}[/blue]\n"
            f"ATS score: [yellow]{ats.score:.2f}[/yellow] ({'PASS' if ats.passed else 'BELOW 0.85'})\n"
            f"Truthful: {'yes' if tailored.is_truthful else 'NO — ' + '; '.join(tailored.truthfulness_notes)}"
        )
        return

    console.print(f"[bold red][ERROR] Unknown resume action '{action}'.[/bold red]")
    raise typer.Exit(code=1)


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
    # Relative export paths are confined to the working directory (blocks
    # `--output ../../secrets.json` style traversal); explicit absolute
    # paths are deliberate user intent and allowed.
    if not out_path.is_absolute():
        resolved = out_path.resolve()
        if not resolved.is_relative_to(Path.cwd().resolve()):
            console.print(
                f"[bold red][ERROR] Relative export path escapes the working "
                f"directory: {output}[/bold red]"
            )
            raise typer.Exit(code=2)
        out_path = resolved

    if format_type.lower() == "json":
        data = [a.model_dump() for a in apps]
        out_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    else:
        # Vault-style open: validated + confined path, O_NOFOLLOW (POSIX),
        # no symlink swap between check and write.
        fd = os.open(
            out_path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
        )
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["application_id", "site", "job_id", "status", "trust_level", "created_at"]
            )
            for a in apps:
                writer.writerow(
                    [
                        a.application_id,
                        a.site,
                        a.job_id,
                        a.status.value,
                        a.trust_level.value,
                        a.created_at,
                    ]
                )

    console.print(
        f"[bold green][OK] Exported {len(apps)} applications to {out_path.resolve()}[/bold green]"
    )


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
            console.print(
                "[bold red]Please specify --cron and --command for add action.[/bold red]"
            )
            return
        entry = sm.add_schedule(cron, command)
        console.print(
            f"[bold green][OK] Schedule added: {entry['schedule_id']} ({cron}) -> {command}[/bold green]"
        )
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


@app.command("tracker")
def tracker_cmd(
    action: str = typer.Argument(
        "list", help="Action: 'list', 'show', 'dashboard', 'dashboard-html'"
    ),
    target: Optional[str] = typer.Argument(
        None, help="Application id ('show') or html path ('dashboard-html')"
    ),
) -> None:
    """Application Tracking System — list, inspect, and dashboard applications."""
    db = DatabaseManager()
    analytics = TrackerAnalytics(db)
    renderer = TrackerRenderer(analytics)

    if action == "list":
        renderer.render_terminal(console, limit=20)
        return

    if action == "show":
        if not target:
            console.print("[bold red]Usage: jobot tracker show <application-id>[/bold red]")
            raise typer.Exit(code=1)
        row = db.get_applications_with_jobs(limit=1000)
        match = next((r for r in row if r["application_id"] == target), None)
        if not match:
            console.print(f"[red]No application with id '{target}'.[/red]")
            raise typer.Exit(code=1)
        console.print_json(data=match)
        return

    if action == "dashboard":
        renderer.render_terminal(console, limit=20)
        return

    if action == "dashboard-html":
        out = Path(target) if target else Path.home() / ".jobot" / "reports" / "dashboard.html"
        path = renderer.render_html_file(out, limit=1000)
        console.print(f"[bold green][OK] Dashboard HTML written to {path}[/bold green]")
        return

    console.print(f"[bold red]Unknown tracker action '{action}'.[/bold red]")
    raise typer.Exit(code=1)


@app.command("digest")
def digest_cmd(
    dry_run: bool = typer.Option(
        True, "--dry-run/--send", help="Render + print only; do not email"
    ),
    period_days: int = typer.Option(7, "--period-days", help="Lookback window in days"),
    output: Optional[str] = typer.Option(None, "--output", help="Write HTML digest to this path"),
) -> None:
    """Generate (and optionally email) the weekly activity digest."""
    db = DatabaseManager()
    generator = DigestGenerator(db, period_days=period_days)
    digest = generator.generate()

    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(digest.html, encoding="utf-8")
        console.print(f"[bold green][OK] Digest HTML written to {out.resolve()}[/bold green]")

    if dry_run:
        console.print(f"[bold cyan]Subject:[/bold cyan] {digest.subject}")
        console.print(digest.text)
        console.print("[yellow](dry run; use --send to email via SMTP config)[/yellow]")
        return

    sender = EmailSender()
    ok, msg = sender.send(digest.subject, digest.html, body_text=digest.text)
    if ok:
        console.print(f"[bold green][OK] Digest emailed: {msg}[/bold green]")
    else:
        console.print(f"[bold red][ERROR] Digest not sent: {msg}[/bold red]")
        console.print(
            "[yellow]Configure smtp.* keys (jobot config set smtp.host ...) for email delivery.[/yellow]"
        )


@app.command("loop")
def loop_cmd(
    mode: str = typer.Option(
        "scan-only", "--mode", help="Loop mode: scan-only | apply-only | digest-only | full-loop"
    ),
    target_title: str = typer.Option(
        "Python Developer", "--target-title", help="Job title search keywords"
    ),
    max_apply: int = typer.Option(10, "--max-apply", help="Max applications per loop iteration"),
    approve: bool = typer.Option(False, "--approve", help="Auto-approve (autonomous trust level)"),
    min_match: float = typer.Option(0.20, "--min-match", help="Minimum match score to consider"),
    limit_per_portal: int = typer.Option(
        5, "--limit-per-portal", help="Postings fetched per portal"
    ),
) -> None:
    """Run one scheduler loop iteration (4 modes)."""
    if mode not in ("scan-only", "apply-only", "digest-only", "full-loop"):
        console.print(
            f"[bold red][ERROR] Unknown loop mode '{mode}'. One of: scan-only, apply-only, digest-only, full-loop[/bold red]"
        )
        raise typer.Exit(code=1)

    vault = CredentialVault()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print("[bold red][ERROR] Candidate profile missing.[/bold red]")
        console.print(
            "[yellow]Please initialize your candidate profile first using: [bold blue]jobot profile init[/bold blue][/yellow]"
        )
        raise typer.Exit(code=1)
    p = vault.load_encrypted_profile(profile_path)

    from jobot.scheduler.loop import LoopExecutor

    executor = LoopExecutor()
    result = asyncio.run(
        executor.run(
            mode,
            p,
            target_title=target_title,
            max_apply=max_apply,
            auto_approve=approve,
            min_match=min_match,
            limit_per_portal=limit_per_portal,
        )
    )

    console.print(f"[bold cyan]Loop [{result.mode}] complete:[/bold cyan]")
    console.print(f"  Discovered: [blue]{result.discovered}[/blue]")
    console.print(
        f"  Applied:    [blue]{result.applied}[/blue] (verified {result.verified}, rejected {result.rejected}, failed {result.failed}, blocked {result.blocked})"
    )
    console.print(f"  Digest sent: [blue]{result.digest_sent}[/blue]")
    for note in result.notes:
        console.print(f"  [dim]- {note}[/dim]")


@app.command("interview")
def interview_cmd(
    action: str = typer.Argument(
        "list", help="Action: 'start', 'list', 'answer', 'review', 'complete'"
    ),
    track: str = typer.Argument("behavioral", help="Track: behavioral | system_design | technical"),
    session_id: Optional[str] = typer.Option(None, "--session", help="Session ID"),
    answer: Optional[str] = typer.Option(None, "--answer", help="Answer text for 'answer' action"),
) -> None:
    """Mock interview sessions with STAR-method coaching."""
    from jobot.interview.coach import MockInterviewer
    from jobot.interview.sessions import SessionStore

    store = SessionStore()
    interviewer = MockInterviewer(store=store)

    if action == "start":
        try:
            session = interviewer.start(track)
        except ValueError as exc:
            console.print(f"[bold red][ERROR] {exc}[/bold red]")
            raise typer.Exit(code=1)
        first = interviewer.next_question(session)
        console.print(
            f"[bold green][OK] Session [blue]{session.session_id}[/blue] started (track: {track})[/bold green]"
        )
        if first:
            console.print(f"[cyan]Q:[/cyan] {first.text}")
        console.print(
            '[yellow]Answer with: jobot interview answer --session <id> --answer "..."[/yellow]'
        )
        return

    if action == "list":
        sessions = store.list()
        if not sessions:
            console.print("[yellow]No interview sessions found.[/yellow]")
            return
        table = Table(title="Interview Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Track")
        table.add_column("Status", style="bold")
        table.add_column("Turns")
        table.add_column("Avg Score")
        for s in sessions:
            table.add_row(
                s.session_id,
                s.track,
                s.status,
                str(len(s.turns)),
                str(interviewer.average_score(s)),
            )
        console.print(table)
        return

    if not session_id:
        console.print("[bold red][ERROR] --session <id> required for this action.[/bold red]")
        raise typer.Exit(code=1)
    sess = store.load(session_id)
    if sess is None:
        console.print(f"[bold red][ERROR] Session '{session_id}' not found.[/bold red]")
        raise typer.Exit(code=1)

    if action == "answer":
        if not answer:
            console.print('[bold red][ERROR] --answer "<text>" required.[/bold red]')
            raise typer.Exit(code=1)
        vault = CredentialVault()
        profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
        if not profile_path.exists():
            console.print(
                "[bold red][ERROR] Candidate profile missing (run 'jobot profile init').[/bold red]"
            )
            raise typer.Exit(code=1)
        profile = vault.load_encrypted_profile(profile_path)
        try:
            turn = asyncio.run(interviewer.answer(sess, answer, profile))
        except ValueError as exc:
            console.print(f"[bold red][ERROR] {exc}[/bold red]")
            raise typer.Exit(code=1)
        console.print(f"[cyan]Q:[/cyan] {turn.question_text}")
        console.print(f"[green]STAR score:[/green] {turn.star_score:.2f}")
        console.print(f"[bold]Coach:[/bold] {turn.feedback}")
        nxt = interviewer.next_question(sess)
        if nxt:
            console.print(f"[cyan]Next Q:[/cyan] {nxt.text}")
        return

    if action == "review":
        table = Table(title=f"Session {sess.session_id} ({sess.track})")
        table.add_column("#")
        table.add_column("Question")
        table.add_column("Score", justify="right")
        table.add_column("Coach Feedback", overflow="fold")
        for i, t in enumerate(sess.turns, start=1):
            table.add_row(str(i), t.question_text, f"{t.star_score:.2f}", t.feedback)
        console.print(table)
        console.print(f"[bold]Average STAR score:[/bold] {interviewer.average_score(sess)}")
        return

    if action == "complete":
        interviewer.complete(sess)
        console.print(
            f"[bold green][OK] Session {session_id} completed (avg {interviewer.average_score(sess)}).[/bold green]"
        )
        return

    console.print(
        f"[bold red][ERROR] Unknown interview action '{action}'. One of: start, list, answer, review, complete[/bold red]"
    )
    raise typer.Exit(code=1)


@app.command("skill-gap")
def skill_gap_cmd(
    limit: int = typer.Option(500, "--limit", help="Max saved postings to analyze"),
) -> None:
    """Analyze skill demand from saved postings vs the candidate profile."""
    vault = CredentialVault()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing (run 'jobot profile init').[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    from jobot.analytics.skill_gap import SkillGapAnalyzer

    report = SkillGapAnalyzer().analyze(profile, limit=limit)
    console.print(
        f"[bold cyan]Skill Gap Report[/bold cyan] — {report.total_postings} postings ({report.sourced_from})"
    )
    console.print(f"Profile skills: [blue]{', '.join(report.profile_skills)}[/blue]")
    if not report.gaps:
        console.print("[green]No gaps detected.[/green]")
        return
    table = Table(title="Top In-Demand Skills Missing From Profile")
    table.add_column("Skill", style="cyan")
    table.add_column("Demand", justify="right")
    for gap in report.gaps[:15]:
        table.add_row(gap.skill, str(gap.demand_count))
    console.print(table)
    console.print("[bold]Learning path recommendations:[/bold]")
    for r in report.recommendations:
        console.print(f"  [dim]- {r}[/dim]")


@app.command("salary")
def salary_cmd(
    role: str = typer.Option("backend", "--role", help="Role key (see --roles)"),
    region: str = typer.Option("India", "--region", help="Region: India | US | EU"),
    roles: bool = typer.Option(False, "--roles", help="List available role keys"),
) -> None:
    """Look up salary benchmarks (shipped reference data; live fetch opt-in via JOBOT_RUN_LIVE_SALARY=1)."""
    from jobot.analytics.salary import SalaryBenchmarker

    benchmarker = SalaryBenchmarker()
    if roles:
        console.print("[cyan]Available roles:[/cyan] " + ", ".join(benchmarker.list_roles()))
        return
    band = benchmarker.benchmark(role, region)
    if band is None:
        console.print(
            f"[bold red][ERROR] No benchmark for role '{role}' / region '{region}'.[/bold red]"
        )
        console.print(f"[yellow]Available roles: {', '.join(benchmarker.list_roles())}[/yellow]")
        raise typer.Exit(code=1)
    table = Table(title=f"{band.role} ({band.region}) — {band.currency}")
    table.add_column("Percentile")
    table.add_column("Annual", justify="right")
    for label, value in (("p25", band.p25), ("p50", band.p50), ("p75", band.p75)):
        table.add_row(label, f"{value:,}")
    console.print(table)
    console.print(
        f"[dim]Source: {band.source}. Reference data is approximate — verify against live offers.[/dim]"
    )


@app.command("outreach")
def outreach_cmd(
    action: str = typer.Argument("presets", help="Action: 'presets', 'draft', 'send'"),
    preset: str = typer.Option("faang_senior", "--preset", help="Preset key"),
    name: str = typer.Option("", "--name", help="Contact first name"),
    company: str = typer.Option("", "--company", help="Contact company"),
    role: str = typer.Option("", "--role", help="Target role at company"),
    output: Optional[str] = typer.Option(None, "--output", help="Write drafted DM to this path"),
) -> None:
    """Cold outreach: list presets, draft DMs, send (with daily cap)."""
    from jobot.outreach.dm import Contact, DMGenerator, OutreachGate
    from jobot.outreach.links import LinkedInPeopleSearchURLBuilder

    generator = DMGenerator()

    if action == "presets":
        presets = generator.presets()
        table = Table(title="Outreach Presets")
        table.add_column("Key", style="cyan")
        table.add_column("Name")
        table.add_column("Tone")
        for key, p in presets.items():
            table.add_row(key, p.name, p.tone)
        console.print(table)
        return

    if not name or not company:
        console.print("[bold red][ERROR] --name and --company are required.[/bold red]")
        raise typer.Exit(code=1)
    contact = Contact(first_name=name, company=company, role=role)

    vault = CredentialVault()
    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    if not profile_path.exists():
        console.print(
            "[bold red][ERROR] Candidate profile missing (run 'jobot profile init').[/bold red]"
        )
        raise typer.Exit(code=1)
    profile = vault.load_encrypted_profile(profile_path)

    dm = asyncio.run(generator.draft(preset, contact, profile))
    if not dm.grounded:
        console.print(
            "[bold red][ERROR] DM failed the grounding gate — review for invented facts.[/bold red]"
        )
        raise typer.Exit(code=1)

    if action == "draft":
        console.print(f"[bold cyan]DM draft ({dm.source}):[/bold cyan]")
        console.print(dm.text)
        console.print(
            f"[dim]LinkedIn search: {LinkedInPeopleSearchURLBuilder().build_for_contact(name, company, role)}[/dim]"
        )
        if output:
            out = Path(output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(dm.text, encoding="utf-8")
            console.print(f"[bold green][OK] Draft written to {out.resolve()}[/bold green]")
        return

    if action == "send":
        if not dm.grounded:
            console.print("[bold red][ERROR] Refusing to send ungrounded DM.[/bold red]")
            raise typer.Exit(code=1)
        gate = OutreachGate()
        if gate.remaining() <= 0:
            console.print(
                f"[bold red][ERROR] Daily DM cap reached ({gate.sent_today()}).[/bold red]"
            )
            raise typer.Exit(code=1)
        from jobot.notify.email import EmailSender

        sender = EmailSender()
        if not sender.is_configured():
            console.print("[bold cyan]Subject:[/bold cyan] Outreach to {name} at {company}")
            console.print(dm.text)
            console.print(
                "[yellow](dry run; SMTP not configured — set smtp.* keys to send)[/yellow]"
            )
            return
        ok, msg = generator.send(dm, contact, gate=gate, email=sender)
        if ok:
            console.print(f"[bold green][OK] DM sent: {msg}[/bold green]")
        else:
            console.print(f"[bold red][ERROR] DM not sent: {msg}[/bold red]")
        return

    console.print(
        f"[bold red][ERROR] Unknown outreach action '{action}'. One of: presets, draft, send[/bold red]"
    )
    raise typer.Exit(code=1)


@app.command("plugin")
def plugin_cmd(
    action: str = typer.Argument("list", help="Action: 'install', 'list', 'audit', 'remove'"),
    target: Optional[str] = typer.Argument(
        None, help="Git URL (install) or plugin name (audit/remove)"
    ),
) -> None:
    """Install, list, audit, or remove plugins (manifest-validated)."""
    from jobot.plugins.auditor import PluginAuditor
    from jobot.plugins.installer import PluginInstaller

    installer = PluginInstaller()

    if action == "install":
        if not target:
            console.print(
                "[bold red][ERROR] git URL required: jobot plugin install <git-url>[/bold red]"
            )
            raise typer.Exit(code=1)
        try:
            manifest = installer.install(target)
        except ValueError as exc:
            console.print(f"[bold red][ERROR] Install failed: {exc}[/bold red]")
            raise typer.Exit(code=1)
        console.print(
            f"[bold green][OK] Installed {manifest.name} v{manifest.version} (permissions: {', '.join(manifest.permissions) or 'none'})[/bold green]"
        )
        audit = PluginAuditor().audit(installer.plugins_dir / manifest.name, manifest)
        console.print(f"[bold]Audit:[/bold] {'PASS' if audit.passed else 'FAIL'}")
        for f in audit.findings:
            console.print(
                f"  [{'red' if f.severity == 'error' else 'yellow' if f.severity == 'warning' else 'dim'}]{f.severity}: {f.message}[/]"
            )
        return

    if action == "list":
        plugins = installer.list_plugins()
        if not plugins:
            console.print("[yellow]No plugins installed.[/yellow]")
            return
        table = Table(title="Installed Plugins")
        table.add_column("Name", style="cyan")
        table.add_column("Version")
        table.add_column("Author")
        table.add_column("Permissions")
        for p in plugins:
            table.add_row(
                p["name"], p["version"], p.get("author", ""), ", ".join(p.get("permissions", []))
            )
        console.print(table)
        return

    if action in ("audit", "remove"):
        if not target:
            console.print(
                f"[bold red][ERROR] plugin name required: jobot plugin {action} <name>[/bold red]"
            )
            raise typer.Exit(code=1)
        if action == "remove":
            if installer.remove(target):
                console.print(f"[bold green][OK] Plugin '{target}' removed.[/bold green]")
            else:
                console.print(f"[bold red][ERROR] Plugin '{target}' not found.[/bold red]")
                raise typer.Exit(code=1)
            return
        dest = installer.plugins_dir / target
        if not dest.exists():
            console.print(f"[bold red][ERROR] Plugin '{target}' not installed.[/bold red]")
            raise typer.Exit(code=1)
        report = PluginAuditor().audit(dest)
        console.print(
            f"[bold]Audit {report.plugin} v{report.version}: {'PASS' if report.passed else 'FAIL'}[/bold]"
        )
        for f in report.findings:
            console.print(
                f"  [{'red' if f.severity == 'error' else 'yellow' if f.severity == 'warning' else 'dim'}]{f.severity}: {f.message}[/]"
            )
        return

    console.print(
        f"[bold red][ERROR] Unknown plugin action '{action}'. One of: install, list, audit, remove[/bold red]"
    )
    raise typer.Exit(code=1)


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
            console.print(
                "[bold red]Please provide run_id to show (e.g. jobot traces show <run_id>)[/bold red]"
            )
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


@app.command("evals")
def evals_cmd(
    action: str = typer.Argument("run", help="Action: 'run'"),
) -> None:
    """Run automated evaluation suite across 6 categories."""
    harness = EvalHarness()
    res = harness.run_eval_suite()

    console.print("\n[bold cyan]=== JoBot Continuous Evaluation Results ===[/bold cyan]")
    console.print(f"Scenarios Evaluated: [bold]{res['total']}[/bold]")
    console.print(f"Scenarios Passed:    [bold green]{res['passed']}[/bold green]")
    console.print(
        f"Overall Pass Rate:   [bold yellow]{int(res['pass_rate'] * 100)}%[/bold yellow]\n"
    )

    table = Table(title="Category Breakdown")
    table.add_column("Category", style="cyan")
    table.add_column("Passed / Total", style="green")

    for cat, scores in res.get("category_scores", {}).items():
        table.add_row(cat, f"{scores['passed']} / {scores['total']}")

    console.print(table)


@app.command("login")
def login_cmd(
    portal: Optional[str] = typer.Argument(
        None, help="Target portal: naukri, linkedin, indeed, etc."
    ),
    status: bool = typer.Option(False, "--status", help="Show active portal login sessions"),
    logout: Optional[str] = typer.Option(
        None, "--logout", help="Clear session for specified portal"
    ),
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
        console.print(
            "[bold red][ERROR] Please specify portal name, --status, or --logout <portal>[/bold red]"
        )
        console.print("[yellow]Usage: jobot login naukri[/yellow]")
        raise typer.Exit(code=1)

    portal_clean = portal.lower().strip()
    console.print(f"[bold cyan]Opening browser login for portal '{portal_clean}'...[/bold cyan]")

    if portal_clean == "naukri":
        flow = NaukriLoginFlow(headless=False)
        success = asyncio.run(flow.execute_login())
        if success:
            console.print(
                f"[bold green][OK] Naukri session successfully saved to {sessions_base / 'naukri'}[/bold green]"
            )
    else:
        session = BrowserSession(portal=portal_clean, headless=False)
        asyncio.run(session.start())
        console.print(
            "[bold green][OK] Browser launched. Complete login in browser window.[/bold green]"
        )


@app.command("config")
def config_cmd(
    action: str = typer.Argument(..., help="Action: 'get', 'set', 'unset', 'show'"),
    key: str = typer.Argument(None, help="Dotted config key, e.g. llm.api_key.gemini"),
    value: str = typer.Argument(None, help="Value to set"),
) -> None:
    """Read/write configuration (three-tier: env, keyring, config.yaml)."""
    manager = ConfigManager()

    if action == "show":
        table = Table(title="JoBot Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        for k, v in manager.show_masked().items():
            table.add_row(k, v if manager.is_secret(k) else f"[green]{v}[/green]")
        console.print(table)
        return

    if not key:
        console.print("[bold red][ERROR] Please specify a config key.[/bold red]")
        raise typer.Exit(code=1)

    if action == "get":
        resolved = manager.get(key)
        if resolved is None:
            console.print(f"[yellow]Config key '{key}' is not set.[/yellow]")
            raise typer.Exit(code=1)
        console.print(str(resolved))
        return

    if action == "set":
        if value is None:
            console.print(
                "[bold red][ERROR] Please specify a value: jobot config set <key> <value>[/bold red]"
            )
            raise typer.Exit(code=1)
        manager.set(key, value)
        location = "OS keyring" if manager.is_secret(key) else str(manager.config_path)
        console.print(f"[bold green][OK] {key} stored in {location}.[/bold green]")
        return

    if action == "unset":
        manager.unset(key)
        console.print(f"[bold green][OK] {key} removed.[/bold green]")
        return

    console.print(
        f"[bold red][ERROR] Unknown config action '{action}'. Use get|set|unset|show.[/bold red]"
    )
    raise typer.Exit(code=1)


@app.command("doctor")
def doctor_cmd(
    export: bool = typer.Option(False, "--export", "-e", help="Export redacted diagnostic zip archive"),
) -> None:
    """Diagnose environment: keyring, storage, profile, and LLM providers."""
    from jobot.doctor import export_diagnostic_bundle, run_doctor_checks

    if export:
        bundle_path = export_diagnostic_bundle()
        console.print(f"[bold green][OK] Diagnostic bundle exported to:[/bold green] {bundle_path}")
        return

    report = run_doctor_checks()
    checks = report.checks
    provider_rows = report.providers
    all_ok = report.all_ok

    table = Table(title="jobot doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="dim")
    for check in checks:
        if check.warn:
            table.add_row(
                check.label,
                "[yellow]WARN[/yellow]" if not check.ok else "[bold green]PASS[/bold green]",
                check.detail,
            )
            continue
        table.add_row(
            check.label,
            "[bold green]PASS[/bold green]" if check.ok else "[bold red]FAIL[/bold red]",
            check.detail,
        )
    console.print(table)

    if any(row["ok"] for row in provider_rows):
        provider_table = Table(title="LLM Providers")
        provider_table.add_column("Provider", style="cyan")
        provider_table.add_column("Status")
        for row in provider_rows:
            provider_table.add_row(
                row["name"],
                "[bold green]PASS[/bold green]"
                if row["ok"]
                else "[yellow]SKIP[/yellow]"
                if row["detail"] == "not configured"
                else "[bold red]FAIL[/bold red]",
                row["detail"],
            )
        console.print(provider_table)

    console.print(
        "[bold green][OK] doctor passed[/bold green]"
        if all_ok
        else "[bold red][ERROR] doctor failed - fix the failing checks above[/bold red]"
    )
    raise typer.Exit(code=0 if all_ok else 1)


@app.command("reset-db")
def reset_db_cmd(
    confirm: bool = typer.Option(False, "--confirm", help="Confirm database reset"),
) -> None:
    """Clear synthetic and test application history from SQLite database."""
    if not confirm:
        user_ok = Confirm.ask(
            "[bold red]Are you sure you want to clear all stored application history in SQLite?[/bold red]"
        )
        if not user_ok:
            console.print("[yellow]Database reset cancelled.[/yellow]")
            return

    db = DatabaseManager()
    deleted_count = db.clear_all_applications()
    console.print(
        f"[bold green][OK] Cleared {deleted_count} application records from database.[/bold green]"
    )


if __name__ == "__main__":
    app()
