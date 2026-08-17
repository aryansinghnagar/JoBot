"""Stdio JSON-RPC 2.0 GUI Sidecar Protocol Server (Layer A/B).

Enables desktop UIs (Tauri 2.x) to execute JoBot commands via stdio
JSON-RPC 2.0 messages. This is the single RPC surface the desktop shell
speaks to; it reuses the same control-plane modules as the CLI so behavior
stays in sync. Secrets are never returned (config values are masked).
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from jobot.adapters import AdapterRegistry, infer_site
from jobot.asp.orchestrator import ApplyOrchestrator
from jobot.config.manager import ConfigManager
from jobot.digest.generator import DigestGenerator
from jobot.discovery.engine import JobDiscoveryEngine
from jobot.gui.error_shield import humanize_exception
from jobot.models.domain import CompensationDetails, JobPosting, PersonalInfo, UserProfile
from jobot.scheduler import SchedulerManager
from jobot.storage.db import DatabaseManager
from jobot.storage.vault import CredentialVault
from jobot.tracker.analytics import TrackerAnalytics
from jobot.obs.tracing import TraceLogger

RUNNER_STATE_PATH = Path.home() / ".jobot" / "runner_state.json"


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = {}
    id: Any


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any = None
    error: Any = None
    id: Any


class StdioSidecarServer:
    """JSON-RPC sidecar with injectable dependencies (hermetic tests)."""

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        vault: Optional[CredentialVault] = None,
        analytics: Optional[TrackerAnalytics] = None,
        scheduler: Optional[SchedulerManager] = None,
        digest: Optional[DigestGenerator] = None,
        engine: Optional[JobDiscoveryEngine] = None,
        orchestrator: Optional[ApplyOrchestrator] = None,
        config: Optional[ConfigManager] = None,
        trace_logger: Optional[TraceLogger] = None,
        profile_loader: Optional[Callable[[], UserProfile]] = None,
    ) -> None:
        self._db = db
        self._vault = vault
        self._analytics = analytics
        self._scheduler = scheduler
        self._digest = digest
        self._engine = engine
        self._orchestrator = orchestrator
        self._config = config
        self._trace_logger = trace_logger
        self._profile_loader = profile_loader
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "ping": self._ping,
            "status": self._status,
            "profile_info": self._profile_info,
            "list_sites": self._list_sites,
            "discover_jobs": self._discover_jobs,
            "apply": self._apply,
            "approve": self._approve,
            "applications": self._applications,
            "tracker_stats": self._tracker_stats,
            "campaign_status": self._campaign_status,
            "pause": self._pause,
            "resume": self._resume,
            "schedule_list": self._schedule_list,
            "schedule_add": self._schedule_add,
            "schedule_remove": self._schedule_remove,
            "digest": self._digest_preview,
            "doctor": self._doctor,
            "config_show": self._config_show,
            "config_get": self._config_get,
            "config_set": self._config_set,
            "config_unset": self._config_unset,
            "traces": self._traces,
            "approvals_list": self._approvals_list,
            "approvals_decide": self._approvals_decide,
            "evidence_manifest": self._evidence_manifest,
            "site_health": self._site_health,
            "candidate_facts": self._candidate_facts,
            "record_candidate_fact": self._record_candidate_fact,
            "import_resume": self._import_resume,
            "profile_save": self._profile_save,
            "export_diagnostics": self._export_diagnostics,
            "setup_browser": self._setup_browser,
        }

    # -- dependency resolution ----------------------------------------------

    def _get_db(self) -> DatabaseManager:
        if self._db is None:
            self._db = DatabaseManager()
        return self._db

    def _get_vault(self) -> CredentialVault:
        if self._vault is None:
            self._vault = CredentialVault()
        return self._vault

    def _get_analytics(self, db: DatabaseManager) -> TrackerAnalytics:
        if self._analytics is None:
            self._analytics = TrackerAnalytics(db)
        return self._analytics

    def _get_scheduler(self) -> SchedulerManager:
        if self._scheduler is None:
            self._scheduler = SchedulerManager()
        return self._scheduler

    def _get_digest(self, db: DatabaseManager) -> DigestGenerator:
        if self._digest is None:
            self._digest = DigestGenerator(db=db)
        return self._digest

    def _get_engine(self) -> JobDiscoveryEngine:
        if self._engine is None:
            self._engine = JobDiscoveryEngine()
        return self._engine

    def _get_orchestrator(self, db: DatabaseManager) -> ApplyOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = ApplyOrchestrator(db)
        return self._orchestrator

    def _get_config(self) -> ConfigManager:
        if self._config is None:
            self._config = ConfigManager()
        return self._config

    def _get_trace_logger(self) -> TraceLogger:
        if self._trace_logger is None:
            self._trace_logger = TraceLogger()
        return self._trace_logger

    def _get_profile(self) -> UserProfile:
        if self._profile_loader is not None:
            return self._profile_loader()
        profile_path = Path.home() / ".jobot" / "profiles" / "default.enc"
        if not profile_path.exists():
            raise FileNotFoundError(
                f"Profile missing at {profile_path} — run 'jobot profile init' first."
            )
        return self._get_vault().load_encrypted_profile(profile_path)

    # -- JSON-RPC plumbing ---------------------------------------------------

    def process_request(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request_dict.get("id")
        method = request_dict.get("method")
        params = request_dict.get("params") or {}

        handler = self._handlers.get(str(method))
        if handler is None:
            return JsonRpcResponse(
                id=req_id, error={"code": -32601, "message": f"Method '{method}' not found"}
            ).model_dump()
        if not isinstance(params, dict):
            return JsonRpcResponse(
                id=req_id,
                error={"code": -32602, "message": "Params must be a JSON object"},
            ).model_dump()
        try:
            result = handler(params)
        except Exception as exc:  # noqa: BLE001
            human_err = humanize_exception(exc)
            err_dict = human_err.to_dict()
            return JsonRpcResponse(
                id=req_id,
                error={
                    "code": err_dict["code"],
                    "message": err_dict["message"],
                    "data": err_dict["data"],
                },
            ).model_dump()
        return JsonRpcResponse(id=req_id, result=result).model_dump()

    def run_loop(self) -> None:
        """Run continuous stdio loop processing JSON-RPC lines."""
        for line in sys.stdin:
            line = line.strip()
            if line:
                try:
                    req = json.loads(line)
                    res = self.process_request(req)
                    sys.stdout.write(json.dumps(res) + "\n")
                    sys.stdout.flush()
                except Exception as e:  # noqa: BLE001
                    err_res = JsonRpcResponse(
                        id=None, error={"code": -32700, "message": f"Parse error: {e}"}
                    ).model_dump()
                    sys.stdout.write(json.dumps(err_res) + "\n")
                    sys.stdout.flush()

    # -- RPC handlers ---------------------------------------------------------

    def _ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "pong", "version": "2.0.0"}

    def _status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        apps = db.list_applications(limit=10)
        return {
            "total_tracked": len(apps),
            "recent": [a.model_dump() for a in apps[:5]],
        }

    def _profile_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._get_profile().model_dump()
        except FileNotFoundError as exc:
            raise ValueError(str(exc))

    def _list_sites(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"sites": AdapterRegistry.list_supported_sites()}

    def _discover_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        portal = str(params.get("portal", "linkedin"))
        keywords = str(params.get("keywords", ""))
        location = str(params.get("location", ""))
        limit = int(params.get("limit", 25))
        company = params.get("company")
        companies = [str(company)] if company else []
        engine = self._get_engine()
        scraper = engine.scraper_for(portal, companies)
        if scraper is None:
            return {"postings": [], "note": f"No scraper for portal '{portal}'"}
        postings = asyncio.run(
            scraper.discover_jobs(
                keywords=keywords, location=location, limit=limit, company=company
            )
        )
        return {
            "postings": [
                {
                    "job_id": p.job_id,
                    "site": p.site,
                    "title": p.title,
                    "company": p.company,
                    "location": p.location,
                    "url": p.url,
                    "description": (p.description or "")[:500],
                }
                for p in postings
            ]
        }

    def _resolve_job(self, params: Dict[str, Any]) -> JobPosting:
        db = self._get_db()
        job_id = params.get("job_id")
        url = params.get("url")
        if job_id:
            job = db.get_job_posting(str(job_id))
            if job is None:
                raise ValueError(f"No saved posting with job id '{job_id}'")
            return job
        if url:
            site = params.get("site") or infer_site(str(url))
            adapter = AdapterRegistry.get_adapter(site)
            return asyncio.run(adapter.parse_job_posting(str(url)))
        raise ValueError("Provide 'job_id' or 'url'")

    def _apply(self, params: Dict[str, Any]) -> Dict[str, Any]:
        job = self._resolve_job(params)
        profile = self._get_profile()
        dry_run = bool(params.get("dry_run", True))
        auto_approve = bool(params.get("auto_approve", False))
        template = str(params.get("template", "default"))
        tone = str(params.get("tone", "classic"))
        engine = params.get("engine")
        orchestrator = self._get_orchestrator(self._get_db())
        result = asyncio.run(
            orchestrator.apply(
                job,
                profile,
                auto_approve=auto_approve,
                dry_run=dry_run,
                template=template,
                engine=str(engine) if engine else None,
                tone=tone,
            )
        )
        return result.model_dump()

    def _approve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        application_id = params.get("application_id")
        if not application_id:
            raise ValueError("Provide 'application_id'")
        app = db.get_application(str(application_id))
        if app is None:
            raise ValueError(f"No application with id '{application_id}'")
        # Record the human decision on the durable approval before the
        # gated submit (G3: approval decisions survive restarts).
        approval_id = (app.form_values or {}).get("_approval_id")
        if approval_id:
            from jobot.execution.engine import ApprovalStatus as _AS
            from jobot.execution.engine import DurableTaskEngine as _DTE

            engine = _DTE(db)
            if engine.get_approval(str(approval_id)) is not None:
                engine.decide_approval(str(approval_id), _AS.APPROVED, decided_by="gui-human")
        orchestrator = self._get_orchestrator(db)
        result = asyncio.run(orchestrator.submit_approved(app))
        return result.model_dump()

    def _applications(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        limit = int(params.get("limit", 50))
        return {"applications": db.get_applications_with_jobs(limit=limit)}

    def _tracker_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        analytics = self._get_analytics(db)
        limit = int(params.get("limit", 1000))
        return {
            "funnel": analytics.funnel(limit=limit),
            "status_counts": analytics.status_counts(limit=limit),
            "recent": db.get_applications_with_jobs(limit=10),
        }

    def _campaign_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        state: Dict[str, Any] = {}
        if RUNNER_STATE_PATH.exists():
            try:
                state = json.loads(RUNNER_STATE_PATH.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                state = {"status": "UNKNOWN"}
        schedules = self._get_scheduler().list_schedules()
        return {
            "runner": state,
            "schedules": schedules,
            "recent": db.get_applications_with_jobs(limit=5),
        }

    def _write_runner_state(self, status: str) -> Dict[str, Any]:
        RUNNER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        state = {"status": status, "updated_at": datetime.now().isoformat()}
        RUNNER_STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
        return state

    def _pause(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._write_runner_state("PAUSED")

    def _resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._write_runner_state("RUNNING")

    def _schedule_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"schedules": self._get_scheduler().list_schedules()}

    def _schedule_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cron = params.get("cron")
        command = params.get("command")
        if not cron or not command:
            raise ValueError("Provide 'cron' and 'command'")
        cmd_str = str(command).strip()
        allowed_cmds = {
            "digest",
            "continuous-campaign",
            "auto-apply",
            "scrape",
            "status",
            "doctor",
            "run",
        }
        first_token = cmd_str.split()[0].lower() if cmd_str else ""
        if first_token == "jobot":
            tokens = cmd_str.split()
            if len(tokens) > 1 and tokens[1].lower() not in allowed_cmds:
                raise ValueError(f"Disallowed schedule subcommand '{tokens[1]}'")
        elif first_token not in allowed_cmds:
            raise ValueError(f"Disallowed schedule command '{cmd_str}'")
        return self._get_scheduler().add_schedule(str(cron), cmd_str)

    def _schedule_remove(self, params: Dict[str, Any]) -> Dict[str, Any]:
        schedule_id = params.get("schedule_id")
        if not schedule_id:
            raise ValueError("Provide 'schedule_id'")
        removed = self._get_scheduler().remove_schedule(str(schedule_id))
        return {"removed": removed}

    def _digest_preview(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db()
        period_days = int(params.get("period_days", 7))
        digest = self._get_digest(db).generate(period_days=period_days)
        return {"subject": digest.subject, "text": digest.text[:4000]}

    def _doctor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from jobot.doctor import run_doctor_checks

        report = run_doctor_checks()
        return {
            "checks": [c.model_dump() for c in report.checks],
            "providers": report.providers,
            "all_ok": report.all_ok,
        }

    def _export_diagnostics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from jobot.doctor import export_diagnostic_bundle

        path = export_diagnostic_bundle()
        return {"status": "exported", "path": str(path)}

    def _config_show(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"config": self._get_config().show_masked()}

    def _config_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key")
        if not key:
            raise ValueError("Provide 'key'")
        str_key = str(key)
        value = self._get_config().get(str_key)
        if value is None:
            raise ValueError(f"Config key '{str_key}' not set")
        if ConfigManager.is_secret(str_key):
            from jobot.secrets import mask

            return {"key": str_key, "value": mask(str(value)), "is_secret": True}
        return {"key": str_key, "value": value, "is_secret": False}

    def _config_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key")
        value = params.get("value")
        if key is None or value is None:
            raise ValueError("Provide 'key' and 'value'")
        self._get_config().set(str(key), str(value))
        return {"set": str(key), "secret": ConfigManager.is_secret(str(key))}

    def _config_unset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        key = params.get("key")
        if not key:
            raise ValueError("Provide 'key'")
        self._get_config().unset(str(key))
        return {"unset": str(key)}

    def _traces(self, params: Dict[str, Any]) -> Dict[str, Any]:
        logger = self._get_trace_logger()
        trace_files = logger.list_traces()
        runs: List[Dict[str, Any]] = []
        for path in reversed(trace_files[-10:]):
            run_id = path.stem
            spans = logger.get_trace_spans(run_id)
            if spans:
                runs.append({"run_id": run_id, "span_count": len(spans), "spans": spans[:50]})
        return {"runs": runs}

    def _approvals_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from jobot.execution.engine import ApprovalStatus as _AS
        from jobot.execution.engine import DurableTaskEngine as _DTE

        db = self._get_db()
        engine = _DTE(db)
        status_str = str(params.get("status", "PENDING")).upper()
        status_enum = _AS(status_str) if status_str in [s.value for s in _AS] else _AS.PENDING
        approvals = engine.list_approvals(status=status_enum)
        return {
            "approvals": [
                {
                    "id": a.id,
                    "task_id": a.task_id,
                    "application_id": a.application_id,
                    "action_type": a.action_type,
                    "risk_level": a.risk_level,
                    "requested_by": a.requested_by,
                    "status": a.status.value,
                    "requested_at": a.requested_at,
                    "expires_at": a.expires_at,
                    "decided_at": a.decided_at,
                    "decided_by": a.decided_by,
                    "decision_reason": a.decision_reason,
                }
                for a in approvals
            ]
        }

    def _approvals_decide(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from jobot.execution.engine import ApprovalStatus as _AS
        from jobot.execution.engine import DurableTaskEngine as _DTE

        approval_id = params.get("approval_id")
        decision_str = str(params.get("decision", "APPROVED")).upper()
        decided_by = params.get("decided_by", "gui-human")
        reason = params.get("reason", "")
        if not approval_id:
            raise ValueError("Provide 'approval_id'")
        decision = _AS(decision_str)
        db = self._get_db()
        engine = _DTE(db)
        rec = engine.decide_approval(
            str(approval_id), decision, decided_by=str(decided_by), reason=str(reason)
        )
        return {
            "id": rec.id,
            "status": rec.status.value,
            "decided_at": rec.decided_at,
            "decided_by": rec.decided_by,
        }

    def _evidence_manifest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        app_id = params.get("application_id")
        if not app_id:
            raise ValueError("Provide 'application_id'")
        manifest_file = Path.home() / ".jobot" / "evidence" / str(app_id) / "manifest.json"
        if not manifest_file.exists():
            return {"found": False, "manifest": None}
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
            return {"found": True, "manifest": data}
        except Exception as exc:  # noqa: BLE001
            return {"found": False, "error": str(exc)}

    def _site_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from jobot.stealth.site_health import SiteHealthMonitor

        monitor = SiteHealthMonitor()
        sites = AdapterRegistry.list_supported_sites()
        return {
            "sites": [
                {
                    "site": s,
                    "status": monitor.get_status(s).status,
                    "success_count": monitor.get_status(s).success_count,
                    "failure_count": monitor.get_status(s).failure_count,
                    "consecutive_failures": monitor.get_status(s).consecutive_failures,
                    "success_rate": monitor.get_status(s).success_rate,
                    "avg_latency_ms": monitor.get_status(s).avg_latency_ms,
                    "last_error": monitor.get_status(s).last_error,
                }
                for s in sites
            ]
        }

    def _candidate_facts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        profile_id = params.get("profile_id", "default")
        db = self._get_db()
        facts = db.list_candidate_facts(profile_id=str(profile_id))
        return {
            "profile_id": profile_id,
            "facts": [f.model_dump() for f in facts],
        }

    def _record_candidate_fact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        fact_type = str(params.get("fact_type", "")).strip()
        fact_value = str(params.get("fact_value", "")).strip()
        profile_id = str(params.get("profile_id", "default")).strip() or "default"
        source = str(params.get("source", "user_gui")).strip()
        if not fact_type or not fact_value:
            raise ValueError("Both 'fact_type' and 'fact_value' are required.")

        from jobot.ai.candidate_truth import CandidateTruthStore

        truth_store = CandidateTruthStore(self._get_db())
        fact = truth_store.record_fact(
            fact_type=fact_type,
            fact_value=fact_value,
            profile_id=profile_id,
            source=source,
            verified=True,
            verified_by="gui_user",
        )
        return {
            "status": "recorded",
            "fact": fact.model_dump(),
        }

    def _import_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path_str = params.get("file_path")
        profile_id = params.get("profile_id", "default")
        if not file_path_str:
            raise ValueError("Provide 'file_path'")
        from jobot.documents.importer import ResumeImporter

        importer = ResumeImporter(db=self._get_db())
        p = Path(file_path_str)
        if not p.exists():
            raise FileNotFoundError(f"Resume file not found: {p}")
        profile, count = asyncio.run(importer.import_and_seed(p, profile_id=str(profile_id)))
        return {
            "profile_id": profile.profile_id,
            "name": f"{profile.personal_info.first_name} {profile.personal_info.last_name}",
            "email": profile.personal_info.email,
            "skills": profile.skills,
            "facts_seeded": count,
        }

    def _profile_save(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update encrypted UserProfile and seed CandidateTruthStore."""
        first_name = str(params.get("first_name", "")).strip()
        last_name = str(params.get("last_name", "")).strip()
        email = str(params.get("email", "")).strip()
        if not first_name or not email:
            raise ValueError("First name and email are required.")

        profile_id = str(params.get("profile_id", "default")).strip() or "default"
        phone = str(params.get("phone", "")).strip()
        location_city = str(params.get("location_city", "")).strip()
        location_country = str(params.get("location_country", "")).strip()

        skills_raw = params.get("skills", [])
        if isinstance(skills_raw, str):
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        elif isinstance(skills_raw, list):
            skills = [str(s).strip() for s in skills_raw if str(s).strip()]
        else:
            skills = []

        target_roles = params.get("target_roles", "")
        if isinstance(target_roles, list):
            target_roles = ", ".join(str(r) for r in target_roles)

        min_salary = float(params.get("min_salary", 0.0) or 0.0)
        notice_days = int(params.get("notice_period_days", 30) or 30)

        personal_info = PersonalInfo(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            location_city=location_city,
            location_country=location_country,
        )

        custom_qa = {}
        if target_roles:
            custom_qa["Target Titles"] = str(target_roles)
        if params.get("years_experience"):
            custom_qa["Years of Experience"] = str(params.get("years_experience"))

        profile = UserProfile(
            profile_id=profile_id,
            personal_info=personal_info,
            skills=skills,
            compensation=CompensationDetails(
                minimum_annual_base_usd=min_salary if min_salary > 0 else None,
                notice_period_days=notice_days,
            ),
            custom_qa_answers=custom_qa,
        )

        vault = self._get_vault()
        vault.save_encrypted_profile(profile)

        # Seed candidate truth store
        from jobot.ai.candidate_truth import CandidateTruthStore

        truth_store = CandidateTruthStore(self._get_db())
        facts = truth_store.seed_from_profile(profile)

        return {
            "status": "saved",
            "profile_id": profile.profile_id,
            "name": f"{first_name} {last_name}".strip(),
            "email": email,
            "skills": profile.skills,
            "facts_seeded": len(facts),
        }

    def _setup_browser(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Download and verify Patchright Chromium browser engine binaries."""
        import subprocess

        try:
            res = subprocess.run(
                [sys.executable, "-m", "patchright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            return {
                "status": "installed" if res.returncode == 0 else "failed",
                "message": "Chromium engine ready"
                if res.returncode == 0
                else (res.stderr or res.stdout),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "message": f"Browser setup encountered an issue: {exc}",
            }
