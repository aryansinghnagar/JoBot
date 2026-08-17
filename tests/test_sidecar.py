"""Hermetic tests for the GUI sidecar JSON-RPC protocol (Layer A/B).

All dependencies are injected as fakes — no database, keyring, network, or
browser access. Verifies every RPC method's request/response contract and the
JSON-RPC error semantics (-32601 method not found, -32602 invalid params).
"""

import json
from pathlib import Path
from types import SimpleNamespace

from jobot.asp.orchestrator import ApplyResult
from jobot.gui.sidecar import StdioSidecarServer
from jobot.models.domain import Application, JobPosting, UserProfile


def _call(server, method: str, params: dict, req_id: int = 1) -> dict:
    return server.process_request(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": req_id}
    )


class FakeDB:
    def __init__(self):
        self.apps: list = []
        self.jobs: dict = {}
        self.job_rows: list = []

    def list_applications(self, limit: int = 50):
        return self.apps[:limit]

    def get_application(self, application_id: str):
        for a in self.apps:
            if a.application_id == application_id:
                return a
        return None

    def get_job_posting(self, job_id: str):
        return self.jobs.get(job_id)

    def get_applications_with_jobs(self, limit: int = 50):
        return self.job_rows[:limit]

    def save_candidate_fact(self, fact):
        return 123

    def list_candidate_facts(self, profile_id="default", fact_type=None, verified_only=False):
        return []


class FakeScraper:
    def __init__(self, postings: list):
        self.postings = postings

    async def discover_jobs(self, keywords="", location="", limit=25, company=None):
        return self.postings[:limit]


class FakeEngine:
    def __init__(self, scraper):
        self.scraper = scraper
        self.last_company = None

    def scraper_for(self, portal: str, companies: list):
        self.last_company = companies[0] if companies else None
        if portal == "nowhere":
            return None
        return self.scraper


class FakeOrchestrator:
    def __init__(self, result: ApplyResult):
        self.result = result

    async def apply(
        self,
        job,
        profile,
        auto_approve=False,
        dry_run=False,
        template="default",
        engine=None,
        tone="classic",
    ):
        return self.result

    async def submit_approved(self, app: Application):
        return self.result


class FakeConfig:
    def __init__(self, store: dict | None = None):
        self.store = store or {}

    def get(self, key: str, default=None):
        return self.store.get(key, default)

    def set(self, key: str, value: str):
        self.store[key] = value

    def unset(self, key: str):
        self.store.pop(key, None)

    def show_masked(self) -> dict:
        return {"llm.default_provider": "anthropic"}

    @staticmethod
    def is_secret(key: str) -> bool:
        return "api_key" in key


class FakeScheduler:
    def __init__(self):
        self.schedules: list = []

    def list_schedules(self):
        return self.schedules

    def add_schedule(self, cron: str, command: str):
        entry = {
            "schedule_id": f"sch_{len(self.schedules) + 1:03d}",
            "cron": cron,
            "command": command,
            "active": True,
        }
        self.schedules.append(entry)
        return entry

    def remove_schedule(self, schedule_id: str):
        self.schedules = [s for s in self.schedules if s.get("schedule_id") != schedule_id]
        return True


class FakeDigest:
    def generate(self, period_days=None, now=None):
        return SimpleNamespace(subject="Weekly Digest", text="Here is your weekly summary.")


class FakeAnalytics:
    def funnel(self, limit: int = 1000):
        return {"total": 3, "pending_approval": 0, "submitted": 1, "verified": 1}

    def status_counts(self, limit: int = 1000):
        return {"submitted": 1, "verified": 1}


class FakeTrace:
    def list_traces(self):
        return [Path("run_abc.jsonl")]

    def get_trace_spans(self, run_id: str):
        return [{"span_id": "s1", "name": "apply", "run_id": run_id}]


def _profile() -> UserProfile:
    return UserProfile(profile_id="sidecar_test", skills=["Python"])


def _posting(job_id: str = "job_1") -> JobPosting:
    return JobPosting(
        job_id=job_id, site="mock_ats", url="http://mock/job/1", title="Engineer", company="Acme"
    )


def _result() -> ApplyResult:
    return ApplyResult(
        saga_id="saga_1",
        job_id="job_1",
        app_status="verified",
        application_id="app_1",
        dry_run=True,
        artifacts={"resume_pdf": "/tmp/resume.pdf"},
        notes=["Dry run"],
    )


def _server(monkeypatch, tmp_path, **overrides) -> StdioSidecarServer:
    defaults: dict = {
        "db": FakeDB(),
        "engine": FakeEngine(FakeScraper([_posting()])),
        "orchestrator": FakeOrchestrator(_result()),
        "config": FakeConfig(),
        "scheduler": FakeScheduler(),
        "digest": FakeDigest(),
        "analytics": FakeAnalytics(),
        "trace_logger": FakeTrace(),
        "profile_loader": _profile,
    }
    defaults.update(overrides)
    server = StdioSidecarServer(**defaults)
    monkeypatch.setattr("jobot.gui.sidecar.RUNNER_STATE_PATH", tmp_path / "runner_state.json")
    return server


def test_sidecar_ping(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "ping", {})
    assert res["result"]["status"] == "pong"
    assert res["result"]["version"] == "2.0.0"


def test_sidecar_unknown_method(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "non_existent_method", {})
    assert res["error"]["code"] == -32601


def test_sidecar_bad_params_type(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = server.process_request(
        {"jsonrpc": "2.0", "method": "ping", "params": "not-an-object", "id": 3}
    )
    assert res["error"]["code"] == -32602


def test_sidecar_status(monkeypatch, tmp_path):
    db = FakeDB()
    app = Application(
        application_id="app_status", job_id="job_1", site="mock_ats", idempotency_key="k1"
    )
    db.apps = [app]
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(server, "status", {})
    assert res["result"]["total_tracked"] == 1
    assert res["result"]["recent"][0]["application_id"] == "app_status"


def test_sidecar_list_sites(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "list_sites", {})
    assert "workday" in res["result"]["sites"]
    assert "linkedin" in res["result"]["sites"]


def test_sidecar_profile_info(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "profile_info", {})
    assert res["result"]["profile_id"] == "sidecar_test"


def test_sidecar_profile_info_missing(monkeypatch, tmp_path):
    def missing():
        raise FileNotFoundError("Profile missing at /x")

    server = _server(monkeypatch, tmp_path, profile_loader=missing)
    res = _call(server, "profile_info", {})
    assert res["error"]["code"] == -32602


def test_sidecar_discover_jobs(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "discover_jobs", {"portal": "linkedin", "keywords": "python"})
    assert len(res["result"]["postings"]) == 1
    assert res["result"]["postings"][0]["title"] == "Engineer"


def test_sidecar_discover_jobs_no_scraper(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "discover_jobs", {"portal": "nowhere"})
    assert res["result"]["postings"] == []
    assert "note" in res["result"]


def test_sidecar_discover_jobs_passes_company(monkeypatch, tmp_path):
    engine = FakeEngine(FakeScraper([]))
    server = _server(monkeypatch, tmp_path, engine=engine)
    _call(server, "discover_jobs", {"portal": "workday", "company": "toptal"})
    assert engine.last_company == "toptal"


def test_sidecar_apply_by_job_id(monkeypatch, tmp_path):
    db = FakeDB()
    db.jobs["job_1"] = _posting()
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(server, "apply", {"job_id": "job_1", "dry_run": True})
    assert res["result"]["app_status"] == "verified"
    assert res["result"]["saga_id"] == "saga_1"


def test_sidecar_apply_unknown_job(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "apply", {"job_id": "missing_job"})
    assert res["error"]["code"] == -32602


def test_sidecar_apply_missing_job_id_and_url(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "apply", {})
    assert res["error"]["code"] == -32602


def test_sidecar_approve(monkeypatch, tmp_path):
    db = FakeDB()
    app = Application(application_id="app_1", job_id="job_1", site="mock_ats", idempotency_key="k1")
    db.apps = [app]
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(server, "approve", {"application_id": "app_1"})
    assert res["result"]["saga_id"] == "saga_1"


def test_sidecar_approve_unknown_application(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "approve", {"application_id": "nope"})
    assert res["error"]["code"] == -32602


def test_sidecar_applications(monkeypatch, tmp_path):
    db = FakeDB()
    db.job_rows = [{"application_id": "a1", "job_id": "j1", "status": "submitted"}]
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(server, "applications", {"limit": 10})
    assert res["result"]["applications"][0]["application_id"] == "a1"


def test_sidecar_tracker_stats(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "tracker_stats", {})
    assert res["result"]["funnel"]["total"] == 3
    assert res["result"]["status_counts"]["submitted"] == 1


def test_sidecar_campaign_status(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    state_file = tmp_path / "runner_state.json"
    state_file.write_text(json.dumps({"status": "PAUSED"}), encoding="utf-8")
    res = _call(server, "campaign_status", {})
    assert res["result"]["runner"]["status"] == "PAUSED"
    assert res["result"]["schedules"] == []


def test_sidecar_pause_resume(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    paused = _call(server, "pause", {})
    assert paused["result"]["status"] == "PAUSED"
    resumed = _call(server, "resume", {})
    assert resumed["result"]["status"] == "RUNNING"


def test_sidecar_schedule_add_list_remove(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    added = _call(server, "schedule_add", {"cron": "0 9 * * 1", "command": "digest"})
    assert added["result"]["schedule_id"] == "sch_001"
    listed = _call(server, "schedule_list", {})
    assert len(listed["result"]["schedules"]) == 1
    removed = _call(server, "schedule_remove", {"schedule_id": "sch_001"})
    assert removed["result"]["removed"] is True


def test_sidecar_digest_preview(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "digest", {"period_days": 7})
    assert res["result"]["subject"] == "Weekly Digest"
    assert "weekly summary" in res["result"]["text"]


def test_sidecar_doctor(monkeypatch, tmp_path):
    import jobot.doctor as doctor_mod

    from jobot.doctor import DoctorCheck, DoctorReport

    fake_report = DoctorReport(
        checks=[DoctorCheck(label="OS keyring", ok=True, detail="Fake")],
        providers=[{"name": "gemini", "ok": True, "detail": "configured + reachable"}],
        all_ok=True,
    )
    monkeypatch.setattr(doctor_mod, "run_doctor_checks", lambda: fake_report)
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "doctor", {})
    assert res["result"]["all_ok"] is True
    assert res["result"]["checks"][0]["label"] == "OS keyring"
    assert res["result"]["providers"][0]["name"] == "gemini"


def test_sidecar_config_show_and_set(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    shown = _call(server, "config_show", {})
    assert shown["result"]["config"]["llm.default_provider"] == "anthropic"

    set_res = _call(server, "config_set", {"key": "llm.default_provider", "value": "anthropic"})
    assert set_res["result"]["set"] == "llm.default_provider"
    assert set_res["result"]["secret"] is False

    set_secret = _call(
        server, "config_set", {"key": "llm.api_key.gemini", "value": "AIzaTESTSECRET12345"}
    )
    assert set_secret["result"]["secret"] is True

    got_secret = _call(server, "config_get", {"key": "llm.api_key.gemini"})
    assert got_secret["result"]["is_secret"] is True
    assert "AIzaTESTSECRET12345" not in got_secret["result"]["value"]
    assert "***" in got_secret["result"]["value"]

    got = _call(server, "config_get", {"key": "llm.default_provider"})
    assert got["result"]["value"] == "anthropic"
    assert got["result"]["is_secret"] is False

    unset = _call(server, "config_unset", {"key": "llm.default_provider"})
    assert unset["result"]["unset"] == "llm.default_provider"


def test_sidecar_config_get_missing(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "config_get", {"key": "llm.api_key.nonexistent"})
    assert res["error"]["code"] == -32602


def test_sidecar_traces(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "traces", {})
    assert len(res["result"]["runs"]) == 1
    assert res["result"]["runs"][0]["run_id"] == "run_abc"
    assert res["result"]["runs"][0]["spans"][0]["name"] == "apply"


def test_sidecar_site_health(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "site_health", {})
    assert "sites" in res["result"]
    assert any(s["site"] == "greenhouse" for s in res["result"]["sites"])


def test_sidecar_evidence_manifest(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "evidence_manifest", {"application_id": "nonexistent_app"})
    assert res["result"]["found"] is False


def test_sidecar_profile_save(monkeypatch, tmp_path):
    db = FakeDB()
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(
        server,
        "profile_save",
        {
            "first_name": "Dev",
            "last_name": "Tester",
            "email": "dev.tester@example.com",
            "phone": "+1234567890",
            "location_city": "Austin",
            "location_country": "USA",
            "skills": ["Python", "FastAPI", "React"],
            "target_roles": ["Software Engineer", "Backend Developer"],
            "min_salary": 120000,
        },
    )
    assert res.get("error") is None
    assert res["result"]["status"] == "saved"
    assert res["result"]["name"] == "Dev Tester"
    assert "Python" in res["result"]["skills"]


def test_sidecar_record_candidate_fact(monkeypatch, tmp_path):
    db = FakeDB()
    server = _server(monkeypatch, tmp_path, db=db)
    res = _call(
        server,
        "record_candidate_fact",
        {
            "fact_type": "skill",
            "fact_value": "Python 3.12, Asyncio, Distributed Systems",
            "profile_id": "default",
        },
    )
    assert res.get("error") is None
    assert res["result"]["status"] == "recorded"
    assert res["result"]["fact"]["fact_type"] == "skill"


def test_sidecar_export_diagnostics(monkeypatch, tmp_path):
    server = _server(monkeypatch, tmp_path)
    res = _call(server, "export_diagnostics", {})
    assert res.get("error") is None
    assert res["result"]["status"] == "exported"
    assert res["result"]["path"].endswith(".zip")
