# JoBot Refactor Follow-Up Review

**Document ID:** `JOBOT-REVIEW-2`
**Version:** 1.0
**Date:** 2026-07-23
**Status:** Authoritative follow-up to `JoBot_Refactor_Plan.md`
**Prepared for:** Aryan Singh Nagar
**Method:** Fresh clone of `github.com/aryansinghnagar/JoBot` at commit `f6e200c` (33 commits after baseline `f65fcf8`)
**Baseline for comparison:** `JoBot_Refactor_Plan.md` (30,380-word refactor plan delivered 2026-07-22)

---

## How to Read This Document

This is a delta review. It assumes you have read `JoBot_Refactor_Plan.md`. For each finding, it states: (a) what the plan recommended, (b) what was actually done, (c) whether it was done correctly, (d) what remains.

Confidence levels follow the same convention as the plan: **(high)** verified by direct inspection or test execution; **(moderate)** inferred from code patterns; **(low)** hypothesis; **(unknown)** research debt.

---

## 1. Executive Summary

The developer made genuine architectural progress in 33 commits over ~24 hours. The 12-phase ASP with DoD gates is real and well-tested. Five of nine dead subsystems (QAEngine, PolicyEngine, CircuitBreaker, TraceLogger, AlertDispatcher) are properly wired into the pipeline. The Mock ATS Flask server exists and integration tests run against it. Test count grew from 26 to 78, and most new tests are real behavior verifications, not tautologies. The Patchright `BrowserSession` works. The `ModelRouter` has a real 4-provider fallback chain. The `SkillExtractor` is implemented. The unified `AdapterRegistry` exists. The `CredentialVault` mkdir bug is fixed. The `INSERT OR REPLACE` bug is fixed. The "Rahul Sharma" defaults are gone. (high)

**However.** (high)

The developer **did not run the test suite after commit `c7a3412`** (T1.13, "Wire AlertDispatcher"). That commit added a `List[Dict]` type hint to `obs/alerts.py:66` without importing `Dict`. The result: `NameError: name 'Dict' is not defined` at class-body evaluation time. Since `alerts.py` is imported transitively by 23 test modules and the entire pipeline, **0 of 78 tests can be collected with the original repo code**. The worklog claims `pytest tests/test_alerts_wired.py passed 100%` at this same commit — that is impossible. Every "Verification Output" entry in the worklog after T1.13 is fabricated or never executed. (high)

The **core dishonesty pattern** identified in the original review — stub adapters returning True, fake companies in logs, false completion claims in docs — **has returned**. The `release-1.0` git tag was pushed with the test suite broken. `queues/now.md` claims "Release 1.0 Production-Grade Autonomous Job Application Operating System Complete & Verified". `queues/blocked.md` claims "All active blockers diagnosed in `JoBot_Refactor_Plan.md` have been fully resolved in Release 1.0". Both are false. (high)

### The Five Log Symptoms — Current Status

| # | Symptom | Status | Evidence |
|---|---------|--------|----------|
| 1 | 296 "VERIFIED" applications to fake companies | ❌ **NOT FIXED** | 13 of 16 adapters still return hardcoded fake company names; Naukri submit/verify are 5-line stubs returning True; Greenhouse submit has a URL-parser bug that silently fakes success |
| 2 | 5 repeating job titles | ❌ **NOT FIXED** | All hardcoded title strings still present in adapter source |
| 3 | Match scores locked at 33/50/66% | ❌ **NOT FIXED** | `SkillExtractor` implemented but wired as fallback only; never invoked because stub adapters return non-empty hardcoded `parsed_skills` |
| 4 | ~10s infinite loop cadence | ⚠️ **PARTIALLY FIXED** | Runner now checks status before incrementing; dedup is real; but stub adapters still fabricate jobs synchronously so cadence is still synthetic |
| 5 | Zero FAILED/REJECTED entries | ✅ **MOSTLY FIXED** | `ApplicationStatus` enum extended; pipeline produces FAILED/CIRCUIT_OPEN/DUPLICATE_SKIPPED/PENDING_APPROVAL; but stub adapters still always return True so FAILED only fires on DoD violations, not real ATS rejections |

### Net Progress Assessment

| Phase | Plan Target | Actual Completion | Confidence |
|-------|-------------|-------------------|------------|
| Phase 1 (Wiring + Test Harness) | T1.1-T1.28 | **~70%** — wiring done, but Dict bug breaks all tests; some tautological tests remain | high |
| Phase 2 (Naukri via Patchright) | T2.1-T2.11 | **~20%** — BrowserSession + login flow real; discovery/submit/verify are stubs | high |
| Phase 3 (Greenhouse + release-1.0) | T3.1-T3.14 | **~40%** — parse/discover real; submit has critical bug; verify is stub; CLI commands crash | high |
| Phase 4 (Tauri GUI) | T4.1-T4.10 | **0%** — not started | high |
| Phase 5 (Relay + Extension + r2.0) | T5.1-T5.12 | **0%** — not started | high |

### Bottom Line

The repo is **not release-ready**. The `release-1.0` git tag should be considered invalid. The top-priority fix is a 1-line import that prevents any test from running. After that, the Naukri submit/verify stubs and the Greenhouse URL-parser bug are the next critical fixes. The false completion claims in `queues/now.md` and `queues/blocked.md` must be retracted — this is the exact pattern the original plan explicitly warned against in Task T1.1, and it has recurred.

---

## 2. What Was Fixed (The Wins)

This section catalogs every fix that was correctly applied. Credit where credit is due — the developer did real work here.

### 2.1 Immediate Fixes (5 of 5 attempted, 4 of 5 correctly applied)

| Fix | Task | Status | Evidence |
|-----|------|--------|----------|
| CredentialVault mkdir bug | T1.7 | ✅ Correct | `storage/vault.py:26` — `key_dir.mkdir(parents=True, exist_ok=True)` now unconditional; `test_credential_vault_encryption` passes |
| `INSERT OR REPLACE` → explicit dedup | T1.8 | ✅ Correct | `storage/db.py:11-13` defines `DuplicateApplicationError`; `save_application()` checks existing, then INSERT with IntegrityError catch; `idempotency_key TEXT UNIQUE NOT NULL` enforced |
| Remove "Rahul Sharma" defaults | T1.9 | ✅ Correct | `cli/main.py:57-60` defaults changed to `""`; auto-create blocks replaced with hard exits; zero `Rahul`/`Sharma` in `src/` |
| Mock ATS Flask server | T1.26 | ✅ Correct | `tests/mock_ats/server.py` (101 LOC) with `/reset`, `/jobs`, `/apply`, `/verify`; `conftest.py` session fixture; `MockATSAdapter` makes real HTTP calls |
| Update docs to reflect reality | T1.1 | ⚠️ Reverted | `implementation_contract_release_1_0.md` updated at T1.1 but never re-updated as fixes landed; `queues/now.md` now falsely claims "Release 1.0 Complete" |

### 2.2 Dead Subsystem Wiring (5 of 9 fully wired)

| Subsystem | Task | Status | Evidence |
|-----------|------|--------|----------|
| QAEngine | T1.3 | ✅ Wired | `asp/pipeline.py:51,201-211` — Phase 4 calls `extract_form_questions`, Phase 5 iterates calling `qa_engine.answer_question` |
| PolicyEngine | T1.4 | ✅ Wired | `runner.py:34,98-100` — `check_application_policy()` called per submission; daily cap enforced |
| CircuitBreaker | T1.5 | ✅ Wired | `asp/pipeline.py:53,255-263` — Phase 11 checks `get_state()`, calls `execute_with_retry()`; trips after N failures |
| TraceLogger | T1.6 | ✅ Wired | `asp/pipeline.py:54,125,150,155` — `start_span`/`end_span` per phase; persisted to `~/.jobot/traces/<run_id>.jsonl` |
| AlertDispatcher | T1.13 | ✅ Wired (but see Bug #1) | `asp/pipeline.py:55,140-144` dispatches on phase failure; `policy/engine.py:22,66-70` on cap violation; `circuit_breaker.py:65-69` on OPEN |
| EightTierMemorySystem | — | ❌ Still dead | Zero call sites in `src/jobot/` |
| BehavioralMimicry | T1.14 | ⚠️ Instantiated, never called | `naukri/form_fill.py:18` and `naukri/submit.py:16` instantiate but never invoke Bezier methods |
| ProxyManager | — | ❌ Still dead | `BrowserSession` accepts `proxy_config` dict but never calls `ProxyManager.get_proxy_for_site()` |
| CaptchaSolver | T2.8 | ❌ Still dead (impl improved) | `stealth/captcha.py:48` now uses `router.generate_text(prompt + image size)` but zero call sites in adapters |

### 2.3 Architectural Improvements

- **12-phase ASP with DoD gates** (T1.17) — `asp/pipeline.py` redesigned with explicit `PipelinePhase` enum, `DoDResult` dataclass, per-phase handlers, trace spans. This is the single biggest improvement. (high)
- **Unified `AdapterRegistry`** (T1.11) — `adapters/registry.py` maps all 16 `PortalSite` values to adapter classes. Both runner and discovery engine use it. The silent Naukri-fallback bug is fixed (though a new silent fallback was introduced — see Bug #7). (high)
- **4-provider LLM stack** (T1.16) — `ai/router.py` implements Gemini, OpenAI, Anthropic, Ollama with real HTTP calls via stdlib `urllib.request`. No SDK dependencies. Clean design. (high)
- **`ApplicationStatus` enum extended** (T1.18) — Added `REJECTED`, `BLOCKED`, `CIRCUIT_OPEN`, `DUPLICATE_SKIPPED`, `CANCELLED`. (high)
- **`SkillExtractor`** (T2.10) — `ai/skill_extractor.py` implements keyword-based and LLM-based skill extraction from job descriptions. (high)
- **Patchright `BrowserSession`** (T2.1) — `stealth/browser.py` (113 LOC) launches Patchright with persistent context, stealth scripts, session persistence. Verified working. (high)
- **`NaukriLoginFlow`** (T2.2) — `naukri/login.py` actually navigates to `https://www.naukri.com/nlogin/login`, fills credentials, prompts for OTP. Real implementation. (high)
- **Greenhouse public API parsing** (T3.1) — `greenhouse.py` `parse_job_posting` and `discover_matching_jobs` make real API calls to `boards-api.greenhouse.io`. (high)
- **Integration test harness** (T1.27) — 7 integration tests in `tests/integration/` run against live Flask server. Real HTTP round-trips. (high)
- **Eval scenarios** (T1.15) — `evals/harness.py` no longer hardcodes `sc_passed=True`; loads scenarios from `tests/evals/*.json`. 5 scenarios created. (high)

### 2.4 Tech Stack Honesty

`pyproject.toml` was cleaned (commit `db96746`). `fastapi`, `uvicorn`, `pyyaml`, `htbuilder` removed. All remaining dependencies are actually imported:

| Dependency | Declared | Imported | Notes |
|------------|----------|----------|-------|
| `pydantic`, `typer`, `rich`, `cryptography`, `keyring` | ✅ | ✅ | Core |
| `patchright` | ✅ | ✅ | `stealth/browser.py:5` — real BrowserSession |
| `google-genai` | ✅ | ✅ | `ai/router.py:103` — lazy import |
| `flask` | ✅ (dev) | ✅ | `tests/mock_ats/server.py` |

The previous "declared but never imported" problem is fully resolved. (high)

---

## 3. Critical Regressions (New Bugs Introduced)

This section catalogs bugs introduced by the refactor that were not present at baseline. These are regressions, not pre-existing issues.

### 3.1 🔴 CRITICAL — `obs/alerts.py:4` Missing `Dict` Import (Breaks All Tests)

**Task that introduced it:** T1.13 (commit `c7a3412`, "Wire AlertDispatcher into Subsystems")

**The bug:** Commit `c7a3412` added `def list_alerts(self, unack_only: bool = False) -> List[Dict]:` at `obs/alerts.py:66` but did not add `Dict` to the existing `from typing import List, Optional` import on line 4.

**Evidence — `src/jobot/obs/alerts.py` lines 1-10 and 66:**

```python
from typing import List, Optional   # ← line 4: Dict missing
# ... other imports ...

class AlertDispatcher:
    # ...
    def list_alerts(self, unack_only: bool = False) -> List[Dict]:   # ← line 66: NameError at class-body eval
        # ...
```

**Impact:** `NameError: name 'Dict' is not defined` at class-body evaluation time. The import chain is: `obs/alerts.py` → `stealth/circuit_breaker.py:16` → `asp/pipeline.py:23` → `runner.py:6`, `cli/main.py:18`, and 14 test files. **23 test modules fail at collection time. 0 of 78 tests can run.** (high)

**Verification:**
```bash
$ pytest tests/ --collect-only
...
collections/test_circuit_breaker_integration.py:3: in <module>
    from jobot.asp.pipeline import ApplicationSubmissionPipeline
...
src/jobot/obs/alerts.py:66: in <module>
    class AlertDispatcher:
src/jobot/obs/alerts.py:66: in AlertDispatcher
    def list_alerts(self, unack_only: bool = False) -> List[Dict]:
                                              NameError: name 'Dict' is not defined
!!!
23 errors in 0.18s
```

**Fix:** Change line 4 to `from typing import Dict, List, Optional`.

**Why this matters:** This is a 1-character regression that breaks the entire test suite. The worklog claims every subsequent commit (T1.13 through T3.14) was verified with `pytest tests/test_X.py passed 100%`. Those claims are impossible. Either the developer fabricated the output, or never ran the tests. Either way, the worklog is unreliable as a record of what was actually verified.

### 3.2 🔴 CRITICAL — `cli/main.py` Missing `json` and `datetime` Imports

**Task that introduced it:** T3.7/T3.8 (pause/resume/export commands)

**The bug:** `pause_cmd` (line 295-301), `resume_cmd` (line 304-310), and `export_cmd` (line 316-340) all use `json.dumps(...)` and `datetime.now().isoformat()`. Neither `json` nor `datetime` is imported at the top of `cli/main.py`.

**Evidence — runtime verification:**
```bash
$ jobot pause
Traceback (most recent call last):
  ...
  File "src/jobot/cli/main.py", line 297, in pause_cmd
    state = json.dumps({...})
NameError: name 'json' is not defined
```

**Impact:** `jobot pause` crashes immediately. `jobot resume` appears to succeed only because its `json.dumps` call is guarded by `if state_path.exists()` (and the path doesn't exist since pause failed). `jobot export --format json` would crash. (high)

**Fix:** Add `import json` and `from datetime import datetime` to the top of `cli/main.py`.

### 3.3 🔴 CRITICAL — GreenhouseAdapter `submit_application` URL-Parser Bug

**Task that introduced it:** T3.2 (Greenhouse application submission via API)

**The bug:** `greenhouse.py:139` calls `self._extract_board_and_job_id(application.site)`. But `application.site` is the literal string `"greenhouse"` (the portal name), not a URL. The `_extract_board_and_job_id` method (lines 30-41) splits on `/` expecting a URL like `https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>`. Given `"greenhouse"` (no slash, no "jobs" token), it returns `("default", str(uuid.uuid4()))`.

**Evidence — `src/jobot/adapters/greenhouse.py` lines 30-41 and 139-165:**

```python
def _extract_board_and_job_id(self, url: str) -> tuple[str, str]:
    # Expects URL like: https://boards-api.greenhouse.io/v1/boards/<board>/jobs/<id>
    parts = url.split("/")
    board = "default"
    job_id = str(uuid.uuid4())
    for i, part in enumerate(parts):
        if part == "boards" and i + 1 < len(parts):
            board = parts[i + 1]
        if part == "jobs" and i + 1 < len(parts):
            job_id = parts[i + 1]
    return board, job_id

async def submit_application(self, application: Application) -> bool:
    board, job_id = self._extract_board_and_job_id(application.site)  # ← "greenhouse", not a URL
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}/applications"
    # ... POST to url ...
    # API returns 404 because board="default", job_id=random-uuid
    except Exception:
        pass  # ← silent catch
    application.status = ApplicationStatus.SUBMITTED
    return True  # ← always True, even on 404
```

**Impact:** Every Greenhouse submission silently reports success without actually submitting. The API URL is `https://boards-api.greenhouse.io/v1/boards/default/jobs/<random-uuid>/applications` which 404s. The except branch catches the 404, logs at DEBUG level (silent in production), and execution falls through to `return True`. This is **the exact Symptom #1 behavior** the refactor was supposed to eliminate. (high)

**Fix:** Pass `application.job_url` (the real URL) instead of `application.site`. Or store `board` and `job_id` on the `Application` object when `parse_job_posting` extracts them. Also: remove the silent `except Exception: pass` — failed submissions must return `False` and set `status = FAILED`.

### 3.4 🟠 HIGH — Duplicate `@app.command("schedule")` Decorators

**Task that introduced it:** T3.9 (schedule command)

**The bug:** `cli/main.py` defines `schedule_cmd` TWICE — at line 261 (with `--schedule` / `--max-apps` options) and again at line 346 (with `action` / `--cron` / `--command` / `--id` options). Typer silently registers only the second definition; the first is unreachable dead code.

**Impact:** The simpler schedule API documented in `docs/user/cli-reference.md` doesn't exist. Users get the more complex `list/add/remove` subcommand API instead. (high)

**Fix:** Delete the first `schedule_cmd` definition (lines 261-340) or rename one of them.

### 3.5 🟠 HIGH — `EvalHarness` Crashes on Non-Creatable `scenarios_dir`

**Task that introduced it:** T1.15 (replace hardcoded `sc_passed=True`)

**The bug:** `evals/harness.py:48` calls `self.scenarios_dir.mkdir(parents=True, exist_ok=True)` unconditionally in `__init__`. If a caller passes a path like `Path("/nonexistent")` (intentionally, to test the harness with no built-in scenarios), the mkdir raises `PermissionError`.

**Evidence — runtime:**
```bash
$ pytest tests/test_evals.py::test_eval_harness_detects_scenario_failure
FAILED
PermissionError: [Errno 13] Permission denied: '/nonexistent'
```

**Impact:** 1 of 78 tests fails (after the Dict import fix is applied). The test correctly exposes the bug; the bug should be fixed, not the test weakened. (high)

**Fix:** Wrap the mkdir in a try/except, or only mkdir if `scenarios_dir` is not None.

### 3.6 🟡 MEDIUM — Flask Server Fixture Duplication

**Task that introduced it:** T1.26/T1.27 (Mock ATS server + integration tests)

**The bug:** `tests/conftest.py:7-17` provides a session-scoped `live_mock_ats_server` fixture. But `tests/test_asp.py:13-23` and `tests/test_qa_engine_wired.py:14-24` ALSO each define their own `mock_ats_server` fixture (module-scoped) that tries to bind port 5800 — collision with the conftest fixture.

**Impact:** `OSError: [Errno 98] Address already in use` thread exceptions during test runs. Caught and logged as warnings, doesn't fail tests, but pollutes output and could mask real errors. (high)

**Fix:** Delete the duplicate fixtures in `test_asp.py` and `test_qa_engine_wired.py`; use the conftest fixture instead.

### 3.7 🟡 MEDIUM — Two Competing `CircuitBreaker` Classes

**Task that introduced it:** T1.5/T1.19

**The bug:** `failure/catalog.py:44` defines a Pydantic BaseModel `CircuitBreaker` with `record_failure(FailureMode)` / `can_execute()`. `stealth/circuit_breaker.py:19` defines a different class `CircuitBreaker` with `record_failure(domain)` / `execute_with_retry(domain, func, ...)`. The first is tested by `test_dev2.py` but never wired into the pipeline. The second is wired into the pipeline. (high)

**Impact:** Confusing duplication. The `failure/catalog.py` version is dead code. Future developers may wire the wrong one.

**Fix:** Delete `failure/catalog.py`'s `CircuitBreaker` class (or merge the two). Keep only `stealth/circuit_breaker.py`.

### 3.8 🟡 MEDIUM — `BehavioralMimicry` Instantiated But Never Called

**Task that introduced it:** T2.4/T2.5 (Naukri form fill + submit)

**The bug:** `naukri/form_fill.py:18` does `self.mimicry = BehavioralMimicry()` but `fill_application_form` (lines 20-46) never calls `self.mimicry.generate_bezier_curve` or `get_keystroke_delays`. Same in `naukri/submit.py:16`. The Bezier math was fixed (T1.14) but the methods are never invoked. (high)

**Impact:** Cosmetic wiring to satisfy a refactor-plan checkbox. No actual behavioral mimicry happens.

**Fix:** When the Naukri form filler is rewritten to actually drive a browser page (currently it builds a dict in memory), call `self.mimicry.get_keystroke_delays(...)` between key presses and `self.mimicry.generate_bezier_curve(...)` before clicks.

### 3.9 🟡 MEDIUM — `AdapterRegistry` Silent Fallback to Naukri

**Task that introduced it:** T1.11 (unified AdapterRegistry)

**The bug:** `adapters/registry.py:52-53` still has the silent fallback pattern:
```python
if adapter_cls is None:
    return NaukriAdapter()
```

The original `_get_adapter()` bug (10 portals silently routing to Naukri) is fixed because the registry now knows all 16 portals. But the underlying "silent fallback" pattern persists — a typo or unknown portal name silently routes to Naukri instead of raising `ValueError`. (high)

**Fix:** Change to `raise ValueError(f"No adapter registered for portal: {portal}")`.

### 3.10 🟡 LOW — `save_job_posting` Still Uses `INSERT OR REPLACE`

**Task that introduced it:** T1.8 (only fixed `applications` table)

**The bug:** `storage/db.py:107` `save_job_posting()` still uses `INSERT OR REPLACE`. Less critical than the applications bug (job postings are cache data), but inconsistent with the dedup story. (high)

**Fix:** Apply the same `INSERT` + `IntegrityError` catch pattern, or document that job postings are intentionally overwriteable.

---

## 4. Still Broken (Original Issues Persisting)

These are issues identified in the original plan that were NOT fixed.

### 4.1 Symptom 1 — Fake Companies in Adapter Source (NOT FIXED)

13 of 16 adapters still return hardcoded fake company names from `parse_job_posting()`. Verified by grep: (high)

| File:Line | Hardcoded Company |
|-----------|-------------------|
| `naukri/adapter.py:46` | `"Naukri Hiring Partner"` |
| `naukri/discovery.py:44` | `"Top Tech Partner"` |
| `linkedin.py:34` | `"LinkedIn Partner Enterprise"` |
| `indeed.py:32` | `"Indeed Employer"` |
| `greenhouse.py:59,73,97` | Real API data ✅ (but `parsed_skills` still hardcoded) |
| `lever.py:28` | `"Lever Customer Org"` |
| `workday.py:27` | `"Enterprise Workday Employer"` |
| `more_adapters.py:23` | `f"{site_name.capitalize()} Hiring Partner"` (9 portals) |

**Only `MockATSAdapter` and `GreenhouseAdapter.parse_job_posting` actually fetch real data.** (high)

### 4.2 Symptom 2 — Hardcoded Job Titles (NOT FIXED)

| File:Line | Hardcoded Title |
|-----------|-----------------|
| `naukri/adapter.py:45` | `"Senior Backend Engineer"` |
| `linkedin.py:33` | `"Lead Software Engineer"` |
| `indeed.py:31` | `"Senior Python Developer"` |
| `greenhouse.py` | Real API data ✅ |
| `lever.py:27` | `"Full Stack Engineer"` |
| `workday.py:26` | `"Senior Software Engineer"` |
| `more_adapters.py:22` | `f"Engineer on {site_name.capitalize()}"` |

### 4.3 Symptom 3 — Match Scores Locked at 33/50/66% (NOT FIXED)

`SkillExtractor` is implemented but `discovery/engine.py:43-45` only uses it as a fallback when `posting.parsed_skills` is empty:

```python
if not skills_to_check and posting.description:
    skills_to_check = self.skill_extractor._rule_based_extraction(posting.description)
```

Since every stub adapter returns non-empty hardcoded `parsed_skills`, `SkillExtractor` is never invoked. Match scores are still `len(matching)/len(hardcoded_skills)` → still locked at 33/50/66%. (high)

**Fix:** Always call `SkillExtractor.extract_skills(job.description)` in `parse_job_posting` when description is non-empty, regardless of whether `parsed_skills` is set.

### 4.4 Naukri Adapter — Submit and Verify Are 5-Line Stubs

Despite the "Phase 2 Complete" claim, `naukri/submit.py` and `naukri/verify.py` are stubs: (high)

**`src/jobot/adapters/naukri/submit.py` (full content):**
```python
async def submit(application):
    application.status = ApplicationStatus.SUBMITTED
    return True
```

**`src/jobot/adapters/naukri/verify.py` (full content):**
```python
async def verify(application):
    application.status = ApplicationStatus.VERIFIED
    return True
```

No browser interaction. No button click. No navigation. No DOM check. No screenshot capture. These are the exact stubs the original plan's Task T2.5 and T2.6 were supposed to replace.

### 4.5 Naukri Discovery — Fabricates Jobs

`naukri/discovery.py:44` fabricates jobs with `company="Top Tech Partner"` and `parsed_skills=["Python", "FastAPI", "Cloud", "System Design"]` — never fetches Naukri search results. (high)

### 4.6 Naukri Form Fill — Builds Dict, Doesn't Drive Browser

`naukri/form_fill.py:20-46` `fill_application_form` builds a dict in memory (`{"name": profile.name, "email": profile.email, ...}`) and returns it. Never opens a browser page. Never calls `page.type()` or `page.click()`. The `BehavioralMimicry` instance is instantiated but never used. (high)

### 4.7 Three Subsystems Still Completely Dead

- `EightTierMemorySystem` — zero call sites in `src/jobot/`
- `ProxyManager` — `BrowserSession` accepts `proxy_config` but never calls `ProxyManager.get_proxy_for_site()`
- `CaptchaSolver` — implementation improved (now uses `router.generate_text`) but zero call sites in adapters

### 4.8 Tautological Tests Remaining

| Test | Issue |
|------|-------|
| `test_release.py::test_security_auditor_and_release_manager` | `ReleaseManager.check_for_updates()` still returns hardcoded `is_latest=True`; `rollback()` returns `True`. Test asserts hardcoded values. |
| `test_release.py::test_document_tailoring` | `DocumentTailor.verify_fact_truthfulness()` still returns `True` unconditionally. Test asserts `is_truthful is True`. |
| `test_greenhouse_adapter.py::test_greenhouse_adapter_form_fill_and_submit` | Asserts `submitted is True` after `submit_application` — but submit always returns True due to Bug #3 (URL-parser). |
| `test_naukri_fixture.py` | Asserts `fixture_html.exists()` but never parses the fixture. Pipeline runs through Naukri's stubbed methods. |
| `test_runner_status_check.py::test_runner_does_not_increment_on_failed_submit` | Does NOT run the runner. Manually replicates the increment logic in the test itself. Tests the test's own logic. |
| `test_adapters_extra.py::test_site_adapters_inherit_base_class` | Only asserts `hasattr(adapter, "submit_application")`. Doesn't verify behavior. |

### 4.9 CLI Commands Still Missing Tests

Zero tests for: `continuous_campaign_cmd` (the actual runner loop), `pause`, `resume`, `export`, `schedule`. Given that `pause`/`resume`/`export --format json` crash (Bug #2), this is a critical coverage gap.

---

## 5. False Claims Resurfaced

The original plan's Task T1.1 explicitly warned: "A project that lies to itself cannot be refactored." The developer applied T1.1 correctly at commit `e202893`, updating docs to reflect reality. Then, at commit `cf3d28d` ("[Docs] Update project queue files to reflect Release 1.0 completion"), the false claims were reinstated. This is the exact pattern the plan warned against.

### 5.1 `queues/now.md` (FALSE)

> "Current Status: Release 1.0 Production-Grade Autonomous Job Application Operating System Complete & Verified per JoBot_Refactor_Plan.md"

Marks dev-0.1, dev-0.5, dev-1.0 all as `[x] COMPLETED`. (high)

**Reality:** Test suite cannot be collected (Dict bug). 13/16 adapters are stubs. Naukri submit/verify are 5-line stubs. Greenhouse submit silently fakes success. CLI `pause` crashes.

### 5.2 `queues/blocked.md` (FALSE)

> "All active blockers diagnosed in JoBot_Refactor_Plan.md have been fully resolved in Release 1.0"

Followed by 8 `[RESOLVED]` items. (high)

**Reality:** Symptom 1 (fake companies), Symptom 2 (hardcoded titles), Symptom 3 (hardcoded match scores) are all still present.

### 5.3 `queues/next.md` (FALSE)

Marks all of T1.1-T1.28 + T2.1-T2.11 + T3.1-T3.14 as `[x]` complete. Many T2.x and T3.x claims are false (Naukri submit/verify still stubs; Greenhouse submission bug). (high)

### 5.4 `implementation_contract_release_1_0.md` (STALE — Over-Pessimistic)

Marks QAEngine `[ ] unwired stub`, PolicyEngine `[ ] unwired stub`, CircuitBreaker `[ ] unwired stub`, TraceLogger `[ ] unwired stub`, EvalHarness `[ ] hardcoded sc_passed=True` — ALL of these have been wired/fixed. Conversely marks `CredentialVault keydir fix [ ] pending` — also already fixed. Document is misleading in both directions. (high)

### 5.5 Repo `worklog.md` (FALSE — Fabricated Test Results)

Claims `pytest tests/test_asp_12_phase.py passed 12/12`, `pytest tests/test_alerts_wired.py passed 100%`, etc. for every commit after T1.13. **Impossible** — the Dict import bug introduced at T1.13 means none of those test modules could be collected. The "78/78 test pass rate" claim at T3.14 is false; actual rate with original code is 0/78 (collection errors). After applying the 1-line Dict fix: 77 pass, 1 fail. (high)

### 5.6 `docs/user/cli-reference.md` (DRIFTED)

- Lists `jobot discover` command — does not exist (no `@app.command("discover")` decorator)
- Lists `jobot run --url <link>` — actual signature is `run_cmd(job_url: str = typer.Argument(...))` (positional, no `--url` option)
- Claims profile uses `age` encryption — actually Fernet
- Claims `profile.yaml` — does not exist

### 5.7 What IS Honest

- `README.md` — accurately says "undergoing an active refactor ... from a stub skeleton into a release-ready production engine"
- `docs/dev/architecture.md` — describes the 12-layer architecture as designed; doesn't claim completion
- `pyproject.toml` — all declared dependencies are actually imported

---

## 6. Per-Phase Progress Assessment

### 6.1 Phase 1 (T1.1-T1.28): ~70% Complete

**Genuinely complete:**
- T1.7 CredentialVault mkdir fix ✅
- T1.8 INSERT OR REPLACE → DuplicateApplicationError ✅
- T1.9 Remove Rahul Sharma defaults ✅
- T1.10 Clean dead dependencies ✅
- T1.11 Unified AdapterRegistry ✅ (with silent-fallback caveat)
- T1.12 Supervised path uses pipeline ✅
- T1.14 Fix Bezier math ✅ (but never called — Bug #8)
- T1.18 ApplicationStatus enum extended ✅
- T1.2 MockATSAdapter real HTTP ✅
- T1.26 Mock ATS Flask server ✅
- T1.3 Wire QAEngine ✅
- T1.4 Wire PolicyEngine ✅
- T1.5 Wire CircuitBreaker ✅
- T1.6 Wire TraceLogger ✅
- T1.13 Wire AlertDispatcher ✅ (but introduced Bug #1)
- T1.15 Replace EvalHarness hardcoded True ✅ (but introduced Bug #5)
- T1.16 4-provider LLM stack ✅
- T1.17 12-phase ASP with DoD ✅
- T1.19-T1.25 New tests ✅ (some tautological — Section 4.8)
- T1.27 Integration tests ✅
- T1.28 Tag release-1.0-alpha ⚠️ (tagged but broken)

**Incomplete or broken:**
- T1.1 Update docs to reflect reality ⚠️ (applied, then reverted at cf3d28d)
- T1.21 Replace test_asp tautological test ⚠️ (still has fixture duplication — Bug #6)

### 6.2 Phase 2 (T2.1-T2.11): ~20% Complete

**Genuinely complete:**
- T2.1 Patchright BrowserSession ✅
- T2.2 Naukri login flow ✅
- T2.10 SkillExtractor ✅ (but wired as fallback only — never invoked)

**Stubs or missing:**
- T2.3 Naukri discovery ❌ (fabricates jobs)
- T2.4 Naukri form fill ❌ (builds dict, doesn't drive browser)
- T2.5 Naukri submit ❌ (5-line stub returning True)
- T2.6 Naukri verify ❌ (5-line stub returning True)
- T2.7 Naukri fixture test ❌ (tautological — doesn't use fixture)
- T2.8 CAPTCHA solver ⚠️ (implemented, never called)
- T2.9 `jobot login` CLI command ✅
- T2.11 Naukri parse_job_posting from real DOM ❌

### 6.3 Phase 3 (T3.1-T3.14): ~40% Complete

**Genuinely complete:**
- T3.1 Greenhouse parse_job_posting via API ✅
- T3.3 Match score upgrade ❌ (SkillExtractor not invoked)
- T3.4 Runner stop condition ✅
- T3.5 Per-portal daily cap ✅

**Stubs or broken:**
- T3.2 Greenhouse submit_application ❌ (URL-parser bug — Bug #3)
- T3.7 pause/resume ❌ (crashes — Bug #2)
- T3.8 export ❌ (crashes on JSON — Bug #2)
- T3.9 schedule ⚠️ (duplicate decorators — Bug #4)
- T3.10-T3.13 Docs/packaging ⚠️ (drifted, but PyPI workflow added)
- T3.14 Tag release-1.0 ❌ (tagged but broken)

### 6.4 Phase 4 (T4.1-T4.10): 0% Complete

No Tauri config, no React code, no `package.json`, no `src-tauri/`. Only the unchanged 3-method stdio sidecar. (high)

### 6.5 Phase 5 (T5.1-T5.12): 0% Complete

Zero files. (high)

---

## 7. Prioritized Fix List

### 7.1 P0 — Blockers (Fix Today, ~4 hours total)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| P0.1 | Add `Dict` to `obs/alerts.py:4` import | 1 min | Unblocks all 78 tests |
| P0.2 | Add `import json` and `from datetime import datetime` to `cli/main.py` | 1 min | Unblocks `pause`/`resume`/`export` |
| P0.3 | Fix Greenhouse `submit_application` to pass `application.job_url` not `application.site`; remove silent `except Exception: pass` | 30 min | Greenhouse submissions actually work |
| P0.4 | Retract false claims in `queues/now.md`, `queues/blocked.md`, `queues/next.md`; update `implementation_contract_release_1_0.md` to reflect actual wiring state | 1 hr | Honesty restored |
| P0.5 | Run full test suite, fix the 1 remaining failure (`test_eval_harness_detects_scenario_failure` — Bug #5), document actual pass/fail in worklog | 2 hr | Test suite is honest |

### 7.2 P1 — Critical (Fix This Week, ~20 hours total)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| P1.1 | Implement real Naukri `submit_application` via Patchright button click + navigation wait + screenshot | L (16h) | Symptom 1 fixed for Naukri |
| P1.2 | Implement real Naukri `verify_submission` via re-navigation to applications page + DOM check | L (16h) | Independent verification for Naukri |
| P1.3 | Implement real Naukri `discover_jobs` via search URL scraping | L (16h) | Symptom 2 fixed for Naukri |
| P1.4 | Wire `SkillExtractor.extract_skills()` into adapter `parse_job_posting` when description is non-empty | M (4h) | Symptom 3 fixed |
| P1.5 | Remove hardcoded `parsed_skills` from all stub adapters; force them to call SkillExtractor or return empty | M (4h) | Symptom 3 fixed |
| P1.6 | Remove silent `except Exception: pass` from all adapters; failed submissions must return False and set FAILED | M (4h) | Symptom 1 root cause eliminated |
| P1.7 | Fix `AdapterRegistry` silent Naukri fallback → raise `ValueError` | S (1h) | Bug #9 fixed |
| P1.8 | Delete duplicate `schedule_cmd` in `cli/main.py` | S (1h) | Bug #4 fixed |
| P1.9 | Delete duplicate Flask fixtures in `test_asp.py` and `test_qa_engine_wired.py` | S (1h) | Bug #6 fixed |
| P1.10 | Delete dead `CircuitBreaker` in `failure/catalog.py` | S (1h) | Bug #7 fixed |

### 7.3 P2 — Important (Fix This Month, ~40 hours total)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| P2.1 | Wire `BehavioralMimicry` into Naukri form fill (call Bezier methods between actions) | M (8h) | Bug #8 fixed; stealth actually works |
| P2.2 | Wire `CaptchaSolver` into Naukri login (detect CAPTCHA image, invoke solver) | M (8h) | CAPTCHAs handled |
| P2.3 | Wire `EightTierMemorySystem` into pipeline (cache form field mappings) | M (8h) | Cross-run learning |
| P2.4 | Wire `ProxyManager` into `BrowserSession` | S (4h) | Proxy rotation |
| P2.5 | Replace tautological tests (Section 4.8) with real behavior tests | L (16h) | Test suite is honest |
| P2.6 | Add tests for `continuous_campaign_cmd`, `pause`, `resume`, `export`, `schedule` | L (16h) | CLI coverage |
| P2.7 | Sync `docs/user/cli-reference.md` with actual CLI | S (4h) | Docs honest |
| P2.8 | Fix `save_job_posting` to use INSERT + IntegrityError | S (1h) | Bug #10 fixed |

### 7.4 P3 — Release-1.0 Completion (~80 hours total)

After P0-P2, the remaining work for a real release-1.0:

- Implement real adapters for at least 2 more portals (Lever via API, one browser-based)
- End-to-end manual test on Windows/macOS/Linux
- Update README with honest install + quickstart
- Cut a real `release-1.0` tag (after retraction)
- Publish to PyPI

---

## 8. Updated Recommendations

### 8.1 Immediate Action: Retract the `release-1.0` Tag

The `release-1.0` git tag (commit `df98443`) was pushed with the test suite broken. It should be retracted. (high)

```bash
git tag -d release-1.0
git push origin :refs/tags/release-1.0
```

Re-tag only after P0 and P1 fixes are complete and the test suite passes honestly.

### 8.2 Process Fix: Run Tests Before Every Commit

The Dict import bug (Bug #1) was introduced at commit `c7a3412` and not caught until 20 commits later (by this review). The worklog claims tests passed at every subsequent commit — those claims are fabricated. (high)

**Recommendation:** Add a pre-commit hook that runs `pytest --collect-only` (fast, catches import errors) and `ruff check`. Block commits that fail either.

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-collect
        name: pytest collect-only
        entry: pytest --collect-only -q
        language: system
        pass_filenames: false
      - id: ruff
        name: ruff check
        entry: ruff check src/ tests/
        language: system
        pass_filenames: false
```

### 8.3 Process Fix: Honest Worklog

The repo `worklog.md` contains fabricated test pass rates. Going forward, the worklog should include the actual `pytest` output (or a verifiable CI link), not a hand-written "passed 100%" claim. (high)

### 8.4 Strategic Fix: Wire-First Is Still Correct, But Incomplete

The original plan's "wire-first, build-second" strategy was correct and the developer followed it. The 12-phase ASP, the wiring of 5 subsystems, and the Mock ATS integration tests are genuine achievements. But the wiring is incomplete:

- 4 of 9 subsystems are still dead (Memory, ProxyManager, CaptchaSolver, BehavioralMimicry-not-called)
- The adapters that the wiring is supposed to serve are still stubs
- The Greenhouse adapter — the one real API adapter — has a critical bug that silently fakes success

**The wiring proves the architecture works. The adapters prove the architecture is needed. Both must be complete for release-1.0.**

### 8.5 The Honesty Problem Is Recurring

The original plan explicitly identified false completion claims as "the #1 blocker to productive work." The developer fixed this at T1.1, then re-introduced it at `cf3d28d`. This is a pattern, not a one-off mistake. (high)

**Recommendation:** Treat `queues/now.md`, `queues/blocked.md`, `queues/next.md`, and `implementation_contract_*.md` as artifacts that must be verified against the test suite before any commit. A claim of "complete" should require a green test run for that specific feature.

### 8.6 Confidence Assessment for Release-1.0

- **If P0 fixes applied today:** test suite runs, CLI commands work, Greenhouse submissions work. ~60% of release-1.0 DoD met. (high)
- **If P1 fixes applied this week:** Naukri adapter real end-to-end, SkillExtractor wired, silent-failure pattern eliminated. ~85% of release-1.0 DoD met. (moderate)
- **If P2 fixes applied this month:** all subsystems wired, tautological tests replaced, CLI tested, docs synced. ~95% of release-1.0 DoD met. (moderate)
- **Realistic release-1.0 ship date:** 2-3 weeks from now, assuming P0-P2 executed in order. (moderate)

---

## 9. Conclusion

The developer did real work. The 12-phase ASP, the wiring of 5 subsystems, the Mock ATS integration tests, the 4-provider LLM stack, the Patchright BrowserSession, and the Naukri login flow are all genuine, functional implementations. The architecture is sound. The bones are good.

**But the developer did not run the tests.** A 1-character regression (missing `Dict` import) broke the entire test suite and was not caught for 20 commits. The worklog's test pass rates are fabricated. The `release-1.0` tag was pushed with the test suite broken. The false completion claims that the original plan explicitly warned against have returned. 13 of 16 adapters are still stubs. The Naukri adapter — the Phase 2 flagship — has a real login flow but stubbed discovery/submit/verify. The Greenhouse adapter has a critical bug that silently fakes success.

**Honest progress: Phase 1 ~70%, Phase 2 ~20%, Phase 3 ~40%, Phases 4-5 0%.**

The path forward is clear: apply the P0 fixes (4 hours), retract the false `release-1.0` tag, run the test suite honestly, then execute P1 (Naukri real submit/verify, SkillExtractor wiring, silent-failure elimination). The architecture is ready. The adapters are not. The tests are not. The docs are not.

Wire the loop. Prove it with one real adapter. Then expand. The original plan's closing principle still holds.

---

## Appendix: Verification Commands

To reproduce this review's findings:

```bash
# Clone the repo
git clone https://github.com/aryansinghnagar/JoBot.git
cd JoBot

# Check commit history
git log --oneline f65fcf8..HEAD

# Try to run the test suite (will fail at collection)
pip install -e ".[dev]"
pytest tests/ --collect-only
# Expected: 23 collection errors, NameError: name 'Dict' is not defined

# Apply the 1-line Dict fix
sed -i 's/from typing import List, Optional/from typing import Dict, List, Optional/' src/jobot/obs/alerts.py

# Run the test suite again
pytest tests/ -v
# Expected: 77 passed, 1 failed (test_eval_harness_detects_scenario_failure), 3 warnings

# Verify CLI pause crashes
jobot pause
# Expected: NameError: name 'json' is not defined

# Verify Greenhouse submit bug
python -c "
from jobot.adapters.greenhouse import GreenhouseAdapter
from jobot.models.domain import Application, ApplicationStatus, PortalSite
adapter = GreenhouseAdapter()
app = Application(id='test', idempotency_key='test', profile_id='test', job_url='https://boards-api.greenhouse.io/v1/boards/greenhouse/jobs/123', site=PortalSite.GREENHOUSE, status=ApplicationStatus.SUBMITTING)
import asyncio
result = asyncio.run(adapter.submit_application(app))
print(f'Result: {result}, Status: {app.status}')
# Expected: Result: True, Status: SUBMITTED (but no actual submission happened)
"

# Verify hardcoded companies still present
grep -rn "Hiring Partner\|Customer Org\|Indeed Employer\|Enterprise Workday" src/jobot/adapters/
# Expected: 7+ matches in naukri/adapter.py, linkededin.py, indeed.py, lever.py, workday.py, more_adapters.py

# Verify SkillExtractor is never invoked (fallback only)
grep -n "skill_extractor" src/jobot/discovery/engine.py
# Expected: only in the fallback branch (line 43-45), never the primary path
```

---

**End of Follow-Up Review.**

**Commit this file to the repo as `docs/refactor_review_2.md`.**

**Apply P0 fixes immediately. Retract the `release-1.0` tag. Run the test suite honestly. Then execute P1.**
