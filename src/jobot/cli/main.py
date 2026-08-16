import asyncio
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Optional
import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from jobot.adapters import AdapterRegistry, SiteAdapter
from jobot.adapters.naukri.login import NaukriLoginFlow
from jobot.ai.qa_engine import QAEngine
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.asp.pipeline import ApplicationSubmissionPipeline
from jobot.config.manager import ConfigManager
from jobot.config.profile import load_llm_settings
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
from jobot.llm.router import ModelRouter
from jobot.llm.providers import PROVIDER_REGISTRY
from jobot.models.domain import ApplicationStatus, CompensationDetails, PersonalInfo, UserProfile
from jobot.obs.alerts import AlertDispatcher
from jobot.obs.manual_test_logger import ManualTestLogger
from jobot.obs.tracing import TraceLogger
from jobot.runner import ContinuousCampaignRunner
from jobot.scheduler import SchedulerManager
from jobot.secrets import mask
from jobot.stealth.browser import BrowserSession
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault
from jobot.tracker.analytics import TrackerAnalytics
from jobot.tracker.render import TrackerRenderer

app = typer.Typer(name="jobot", help="Autonomous Job Application Operating System CLI")
console = Console()
err_console = Console(stderr=True)
test_logger = ManualTestLogger()


def get_adapter(site: str) -> SiteAdapter:
    return AdapterRegistry.get_adapter(site)


def infer_site(url: str) -> str:
    """Best-effort site inference from a job URL."""
    lowered = url.lower()
    if "lever.co" in lowered:
        return "lever"
    if "greenhouse.io" in lowered:
        return "greenhouse"
    if "linkedin.com" in lowered:
        return "linkedin"
    if "naukri.com" in lowered:
        return "naukri"
    if "indeed.com" in lowered:
        return "indeed"
    if "jobs.ashbyhq.com" in lowered:
        return "ashby"
    if "smartrecruiters.com" in lowered:
        return "smartrecruiters"
    if "boards.greenhouse.io" in lowered:
        return "greenhouse"
    return "greenhouse"


def _resolve_job(
    job_id: Optional[str],
    url: Optional[str],
    site: Optional[str],
    db: DatabaseManager,
    out_console: Console,
) -> Any:
    """Resolve a JobPosting from a saved job id or a URL (live parse)."""
    from jobot.models.domain import JobPosting

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
        site_name = site or infer_site(url)
        adapter = get_adapter(site_name)
        job = asyncio.run(adapter.parse_job_posting(url))
        if not job.title or not job.job_id:
            out_console.print("[bold red][ERROR] Could not parse job posting from URL.[/bold red]")
            return None
        return job
    out_console.print("[bold red][ERROR] Provide --job-id or --url.[/bold red]")
    return None


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
                    asyncio.run(pipeline.submit_and_verify(app_res))
                    if app_res.status in (ApplicationStatus.VERIFIED, ApplicationStatus.SUBMITTED):
                        console.print(
                            f"[bold green][OK] Application SUBMITTED & VERIFIED for {job.company}![/bold green]\n"
                        )
                    else:
                        console.print(
                            f"[bold red][ERROR] Submission failed: {app_res.error_message}[/bold red]\n"
                        )
                else:
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

    if format_type.lower() == "json":
        data = [a.model_dump() for a in apps]
        out_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    else:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
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
    target: Optional[str] = typer.Argument(None, help="Application id ('show') or html path ('dashboard-html')"),
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
def doctor_cmd() -> None:
    """Diagnose environment: keyring, storage, profile, and LLM providers."""
    checks: list[tuple[str, bool, str]] = []
    all_ok = True

    py_ok = sys.version_info >= (3, 11)
    checks.append(("Python >= 3.11", py_ok, f"{sys.version.split()[0]}"))

    try:
        import keyring

        backend = keyring.get_keyring()
        backend_name = backend.__class__.__name__
        keyring_ok = "fail" not in backend_name.lower() and "null" not in backend_name.lower()
        checks.append(("OS keyring", keyring_ok, backend_name))
    except Exception as exc:  # noqa: BLE001
        checks.append(("OS keyring", False, str(exc)))

    try:
        db = DatabaseManager()
        db_ok = True
        checks.append(("SQLite database", db_ok, str(db.db_path)))
    except Exception as exc:  # noqa: BLE001
        checks.append(("SQLite database", False, str(exc)))

    try:
        vault = CredentialVault()
        checks.append(("Encryption vault", True, str(vault.key_dir)))
    except Exception as exc:  # noqa: BLE001
        checks.append(("Encryption vault", False, str(exc)))

    profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
    profile_ok = profile_path.exists()
    checks.append(
        (
            "Profile (encrypted)",
            profile_ok,
            str(profile_path) if profile_ok else "missing - run 'jobot profile init'",
        )
    )

    engine_ok = tex_engine_available()
    checks.append(
        (
            "LaTeX engine (lualatex/xelatex)",
            True,
            "available" if engine_ok else "not found - reportlab fallback will be used",
        )
    )
    poppler_ok = pdftotext_available()
    checks.append(
        (
            "pdftotext (poppler)",
            True,
            "available" if poppler_ok else "not found - pdfminer fallback will be used",
        )
    )
    checks.append(("PDF rendering", True, "reportlab (pure python) always available"))

    router = ModelRouter(daily_budget_usd=load_llm_settings().daily_cost_cap_usd)
    provider_rows: list[tuple[str, bool, str]] = []
    for name in PROVIDER_REGISTRY:
        configured = name in router.list_configured_providers()
        reachable = asyncio.run(router.health_check(name)) if configured else False
        provider_rows.append(
            (
                name,
                configured and reachable,
                "configured + reachable"
                if reachable
                else ("configured" if configured else "not configured"),
            )
        )

    any_provider = any(configured for _, configured, _ in provider_rows)
    checks.append(
        (
            "LLM provider (>= 1 configured)",
            any_provider,
            f"{sum(1 for _, c, _ in provider_rows if c)}/{len(provider_rows)}",
        )
    )

    table = Table(title="jobot doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail", style="dim")
    for label, ok, detail in checks:
        if label == "Profile (encrypted)":
            table.add_row(
                label,
                "[yellow]WARN[/yellow]" if not ok else "[bold green]PASS[/bold green]",
                detail,
            )
            continue
        all_ok = all_ok and ok
        table.add_row(
            label, "[bold green]PASS[/bold green]" if ok else "[bold red]FAIL[/bold red]", detail
        )
    console.print(table)

    if any_provider:
        provider_table = Table(title="LLM Providers")
        provider_table.add_column("Provider", style="cyan")
        provider_table.add_column("Status")
        for name, ok, detail in provider_rows:
            provider_table.add_row(
                name,
                "[bold green]PASS[/bold green]"
                if ok
                else "[yellow]SKIP[/yellow]"
                if detail == "not configured"
                else "[bold red]FAIL[/bold red]",
                detail,
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
