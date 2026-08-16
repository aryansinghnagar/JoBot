text

# JoBot Unified Master Plan: From Prototype to Production‑Ready Autonomous Job‑Application Agent

**Version:** 1.0 · 2026‑08‑15 · **Status:** APPROVED – PENDING EXECUTION  
**Target:** Transform JoBot from a feature‑complete prototype into a production‑grade, releasable, commercially viable open‑source product (v1.0.0+).  
**Guiding Principles:** AGENTS.md (repo root) – zero fabrication, verification‑first, file‑based state, one‑change eval loops, momentum queues, open standards over lock‑in.

---

## Executive Summary

JoBot already possesses the architecture of an ambitious local‑first agent platform: an asynchronous execution fabric, task graph concepts, application‑state protocol, saga orchestration, provider‑neutral LLM routing, browser automation, encrypted storage, OS keyring integration, policy controls, memory, tracing, evaluations, adapters, GUI, CI, SBOM generation, and PyPI publishing.

**The core recommendation is not to rewrite JoBot and not to immediately add another large collection of capabilities.** The next milestone must be:

> **Make one end‑to‑end job application durable, verifiable, recoverable, observable, secure, and reproducible under failure.**

Only after that foundation is proven should JoBot aggressively expand to additional job boards, networking, market intelligence, large‑scale application campaigns, self‑improvement, and broader agent capabilities.

### Core Production Invariant

NO ACTION WITHOUT A STATE
NO STATE WITHOUT AN EVENT
NO COMPLETION WITHOUT VERIFICATION
NO SIDE EFFECT WITHOUT POLICY
NO RETRY WITHOUT IDEMPOTENCY
NO LONG RUN WITHOUT CHECKPOINT
NO MEMORY WITHOUT PROVENANCE
NO AUTONOMY WITHOUT MEASUREMENT
text


---

## Part I: Current State Assessment & Baseline

### 1.1 Verified Baseline (2026‑08‑15)

| Area | State |
|------|-------|
| Tests | pytest 359 passed / 13 skipped (13 = live opt‑in); vitest 18/18; prettier clean |
| Static Analysis | ruff check/format clean; mypy clean (116 files, strict) |
| CI | 3‑OS × 2‑Python quality matrix; npm‑quality; SBOM + provenance attestation; CodeQL weekly; Dependabot |
| Release | PyPI publish‑on‑release workflow (token auth); `release‑1.0` + `release‑2.0` tags pushed |
| Packaging | Multi‑stage Dockerfile + compose; Tauri 2 shell (`gui/src‑tauri`) |
| Built‑in Ops | `jobot backup/migrate/trace/quarantine/doctor/config`; keyring + Fernet secrets; 22‑method JSON‑RPC sidecar; scheduler + daily caps |
| Adapters | Honest no‑fabrication: naukri/linkedin/workday live browser opt‑in (`JOBOT_RUN_LIVE_BROWSER=1`), lever/greenhouse/ashby/smartrecruiters real APIs, 8 JobSpy boards |
| Architectural Strengths | Adapter registry + honest per‑site adapters; saga orchestrator with DoD gates; typed contract doc; doctor; hermetic test culture (359 tests, fake browser/HTTP); no‑fabrication invariant enforced by tests; sidecar RPC with injectable deps; GUI SSR‑safe views |

### 1.2 Current Maturity Estimate

| Area | Current | Target |
|------|---------:|-------:|
| Domain Model | 7/10 | 9/10 |
| Job Adapters | 6/10 | 9/10 |
| Application Workflow | 7/10 | 9.5/10 |
| Durable Execution | 4/10 | 9.5/10 |
| Task Graph | 3/10 | 9/10 |
| State Persistence | 6/10 | 9/10 |
| Idempotency | 6/10 | 9.5/10 |
| Saga/Compensation | 5/10 | 9/10 |
| Browser Automation | 5/10 | 9/10 |
| Security | 6/10 | 9/10 |
| Policy/Governance | 5/10 | 9/10 |
| LLM Routing | 6.5/10 | 9/10 |
| Memory | 4/10 | 8.5/10 |
| Observability | 5/10 | 9/10 |
| Evals | 5/10 | 9/10 |
| GUI/Control Plane | 5/10 | 9/10 |
| CI | 7/10 | 9.5/10 |
| Packaging/Release | 4/10 | 9.5/10 |
| Documentation | 6/10 | 9/10 |
| **Overall Production Readiness** | **~5/10** | **9/10** |

### 1.3 Known Gaps

1. **Version Drift:** `pyproject.toml` 0.1.0, root `package.json` 0.1.0, `gui` 2.0.0, `tauri.conf.json` 2.0.0 – no single source of truth.
2. **Missing Governance Files:** No `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT`, issue/PR templates, `FUNDING.yml`.
3. **Insufficient README:** Only 25 lines – no quickstart, badges, screenshots, architecture.
4. **Security Vulnerabilities:** `npm audit` shows 3 vulnerabilities (1 moderate, 2 high) – not gated in CI; no `pip‑audit`/osv‑scanner.
5. **Tauri Security:** CSP is `null`; capability permissions not re‑audited.
6. **Placeholder Icons:** Solid‑colour icons; no desktop CI builds, code signing, or auto‑updater.
7. **Rust Unverified:** `cargo check` never run (no C toolchain on dev machine; CI has none either).
8. **Test Gaps:** No coverage threshold gate; no failure injection, soak, or GUI E2E tests.
9. **Telemetry/Privacy:** None; no privacy documentation.
10. **Stale Queues:** `queues/improve.md` lists 9 subsystems as unwired though worklog shows QAEngine/PolicyEngine/CircuitBreaker/TraceLogger/AlertDispatcher wired in Phase 1.
11. **Technical Debt:** Browser layer (`stealth/`) selectors hard‑coded; no central registry, no healing, no drift simulation tests; `proxy.py` and `captcha.py` vision paths unwired.
12. **Adapter Families:** Workday cxs‑API pattern is bespoke; workable/icims/sap/ultipro need generalisation.
13. **Memory System:** `form_field_memory` tier not persisted/wired (8‑tier system partially built).
14. **Event Bus:** `obs/` has alerts/tracing; no event bus; AlertDispatcher not wired to scheduler/GUI.
15. **Contracts:** Adapter protocol duck‑typed; no runtime schema validation at phase boundaries.

---

## Part II: Architectural Strategy & Design Principles

### 2.1 Core Architectural Principles (from AGENTS.md)

**Non‑negotiable design bets:**

1. **Start with a powerful single‑agent baseline.** Add agents only when work is embarrassingly parallel, a reviewer must be separate, the task is long‑running with background specialists, or different machines/tool environments are required.
2. **Separate open‑ended reasoning from deterministic workflows.** Workflows handle routing, retries, approvals, timers, checkpoints, fan‑out/fan‑in. Agents handle ambiguous reasoning, research, creative problem solving.
3. **Build a task graph, not a chat transcript with side effects.** Real state = goals, tasks, events, artifacts, metrics, approvals, incidents, knowledge. Chat is one surface over that.
4. **Per‑project state file‑first.** Markdown/repo files are canonical for planning, tasks, knowledge, decisions, handoffs, artifacts. Structured stores for queueing, events, sessions, metrics, costs, approvals, operational indexing.
5. **Verification is a separate concern.** Never let the same unverified step both produce and certify. Prefer planner/executor → verifier → reviewer/approval.
6. **Research mode and action mode are distinct.** Research: breadth, citation quality, uncertainty tracking, progress visibility. Action: execution safety, approvals, state changes, rollback.
7. **Browser and desktop automation are real infrastructure** – own reliability, session persistence, replayability, verification methods.
8. **Memory is a product surface** – inspectable, editable, searchable, versioned. Hidden memory is a liability.
9. **Typed interfaces and explicit schemas** for tasks, tool calls, artifacts, decisions, eval results.
10. **Adapters over lock‑in** – wrap model providers, tools, browser backends, storage, execution runtimes.
11. **Local‑first default, cloud‑scale expansion path.** Repo‑local state, scripts, inspectability first; workers, schedulers, dashboards, heavy tasks move to remote later.
12. **Most gains come from better loops, not bigger prompts.** Stronger task specs, better tools, cleaner verification, improved memory, clearer dashboards, tighter evals, better routing.
13. **Every repeated success becomes a reusable asset** – promote trajectories into skills, playbooks, macros, workflows, templates.
14. **Every repeated failure becomes a test or guardrail.**
15. **Optimise the full loop before breadth.** A wide but broken system is worse than narrow but closed‑loop.

### 2.2 Recommended Default Implementation Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Control Plane | Hybrid – REST for CRUD/dashboards/history/admin/integration; WebSockets/streaming for live output, task dispatch, interventions, alerts, machine presence | Supports both synchronous queries and real‑time streaming |
| Execution Topology | Hub‑and‑worker – durable queueing and policy in hub; tool execution on workers near the real machine environment | Decouples scheduling from execution |
| Queue Persistence | Persist tasks in a real store before dispatching; explicit `goal → task graph → assignment → result` lifecycle | Never rely on in‑memory messages alone |
| Database | Start with SQLite WAL for single‑server control plane; move to Postgres only when concurrency/hosting/scale demands | Local‑first, simple, reliable |
| State Split | Operational indexing (tasks, sessions, agents, approvals, budgets, metrics, incidents, trust scores) in structured storage; canonical per‑project state (plan, tasks, knowledge, decisions, contract, status, handoff, failure notes, artifacts, runbooks) in markdown/visible files | Visibility + queryability |
| Task Locking | Atomically lock before dispatch; lock only pending tasks; unlock only on completion, explicit failure, or timeout | Prevents duplicate execution |
| Session Visibility | Every agent run creates a visible session humans can inspect | Observability |
| Retry Policy | Retry once automatically for ordinary failure; then change strategy or escalate | Avoid infinite retry storms |
| Approval Model | Gate before dispatch, not only after execution; combine explicit user rules with automatic decision tiers based on content and risk | Safe by default |
| Trust Model | Per user and per skill/domain, not only globally; promote autonomy based on real task outcomes | Fine‑grained control |
| Budget Model | Per task, per goal, per machine/worker, per month; auto‑pause or require approval when exceeded | Cost control |

---

## Part III: Unified Execution Roadmap

### Phase Overview

| Phase | Theme | Weeks | Key Deliverables |
|-------|-------|-------|-------------------|
| **P0** | Baseline Freeze & Foundation | 1‑2 | Architecture inventory, dependency inventory, test baseline, eval baseline, security baseline, production‑readiness scorecard |
| **P1** | Vulnerability Fixes & CI/CD Hardening | 2‑3 | All Dependabot/CodeQL alerts closed; CI security gates; version unification |
| **P2** | Durable Execution Core | 2‑4 | Persistent tasks, leases, heartbeats, attempts, events, checkpoints, retry policies, quarantine, cancellation, recovery |
| **P3** | Application State Correctness | 2‑3 | Formal state machine, event ledger, effect ledger, idempotency, verification, unknown states, durable approval, reconciliation |
| **P4** | Browser & Adapter Reliability | 3‑5 | Browser pool, session lifecycle, selector registry+healing, evidence capture, CAPTCHA boundary, ATS family expansion |
| **P5** | AI Reliability & Evaluation Platform | 2‑4 | Typed LLM contracts, prompt registry+versioning, capability‑aware routing, cost ledger, independent reviewers, candidate truth system |
| **P6** | Production Artifacts & Release Engineering | 3‑4 | PyPI trusted publishing, Docker multi‑arch images, desktop CI builds, code signing, auto‑update, CSP hardening |
| **P7** | Control Plane / GUI Completion | 3‑5 | Dashboard, task inspector, approval inbox, evidence viewer, trace viewer, cost dashboard, incident dashboard, Kanban |
| **P8** | Capability Expansion (P0 Features) | 4‑6 | Kanban tracker, form autofill+answer bank, selector healing, ATS family extension, follow‑up automation, export/import, ATS scoring, apply‑method classification |
| **P9** | Telemetry, Privacy & Documentation | 2‑3 | Crash reporting (Sentry), anonymous usage analytics, privacy doc, health report, docs site, community files |
| **P10** | Release & Launch | 1‑2 | v1.0.0 tag, release pipeline, announcement, post‑launch roadmap |

---

## Part IV: Detailed Work Packages

### P0 — Baseline Freeze & Foundation (Weeks 1‑2)

**Goal:** Establish an immutable baseline, understand everything before changing.

| ID | Task | Verification |
|----|------|-------------|
| P0.1 | Full architecture inventory – document every module, dependency, entrypoint | Inventory documented |
| P0.2 | Dependency inventory – all Python, npm, Rust dependencies with licenses | Dependency matrix complete |
| P0.3 | Runtime matrix – supported Python versions (3.11/3.12/3.13), OSes | Matrix documented |
| P0.4 | Test baseline – record current coverage, pass rates, skip reasons | Baseline report |
| P0.5 | Eval baseline – run all existing evaluations, record results | Eval report |
| P0.6 | Security baseline – run security scans, record findings | Security report |
| P0.7 | Performance baseline – record key path latencies, memory usage | Performance report |
| P0.8 | Production‑readiness scorecard – baseline current state against all dimensions | Scorecard complete |

### P1 — Vulnerability Fixes & CI/CD Hardening (Weeks 2‑4)

**Goal:** Fix all known vulnerabilities, harden CI/CD pipelines. (References plan5 W1‑W4)

| ID | Task | Verification |
|----|------|-------------|
| P1.1 | **npm stack upgrade:** vite 5.4.21 → 8.2.1; vitest → 4.1.10; @vitejs/plugin‑react → 6.0.5; prettier → 3.9.6; @tauri‑apps/api → 2.11.1 | `npm audit` clean; vitest 18/18 passes; vite build succeeds |
| P1.2 | **Node engine constraints:** add `engines: {"node": ">=20.19.0"}` + `packageManager` | CI node matrix 20/22 |
| P1.3 | **CodeQL URL sanitisation:** rewrite `infer_site()` using `urllib.parse.urlsplit` exact netloc match; unknown URLs raise `ValueError`; fix `workday.py:95` | All 9 CodeQL alerts close; new adversarial tests pass |
| P1.4 | **glib RUSTSEC‑2024‑0429:** document accepted risk in SECURITY.md (unreachable code path, no fix in tauri 2/gtk3 tree) | Documented; Dependabot cargo updates active |
| P1.5 | **CI hardening:** Ruff use pyproject defaults; pin tool versions; new `security‑gates` job (npm audit --audit‑level=high, pip‑audit, gitleaks, actionlint); SHA‑pin all actions; CodeQL add Rust; `dev` branch cleanup | All CI jobs green; actionlint clean; gitleaks 0 findings |
| P1.6 | **Version unification:** create `scripts/sync_versions.py` aligning pyproject/root package.json/gui package.json/tauri.conf.json | All four files match; CI check fails on drift |
| P1.7 | **Python packaging metadata:** `license = "AGPL‑3.0‑only"` (SPDX); add classifiers, keywords, `[project.urls]` | `python -m build` clean; `twine check` clean |
| P1.8 | **mypy Python version:** `python_version = "3.11"` (match lowest supported) | mypy passes |

### P2 — Durable Execution Core (Weeks 4‑7)

**Goal:** Build the persistent task system so execution can survive failure. (References Plan1 §3‑5)

| ID | Task | Verification |
|----|------|-------------|
| P2.1 | **Persistent task entities:** create Task, TaskAttempt, TaskLease, TaskEvent, TaskArtifact, TaskDependency tables | Schema migrations applied |
| P2.2 | **Task state machine:** PENDING→READY→CLAIMED→RUNNING→WAITING→RETRYING→VERIFYING→COMPLETED/FAILED/QUARANTINED/CANCELLED/UNKNOWN | State transition tests pass |
| P2.3 | **Atomic task leasing:** database‑level conditional updates for atomic claiming; lease timeouts and heartbeats | Multiple workers cannot claim same task |
| P2.4 | **Event ledger:** create `events` table (event_id, aggregate_type, aggregate_id, event_type, event_version, payload, actor, correlation_id, causation_id, created_at) | Event audit tests pass |
| P2.5 | **Effect ledger:** create `ExternalEffect` table (effect_id, task_id, application_id, effect_type, idempotency_key, request_hash, started_at, completed_at, status, external_reference, verification_state, compensation_state) | Compensation tests pass |
| P2.6 | **Checkpoint/resume:** checkpoint after key phases; resume after process death | Kill worker during major execution phases and resume correctly |
| P2.7 | **Retry policies:** configurable retries (exponential backoff); retry with variation (not same exact command) | Retry tests pass |
| P2.8 | **Quarantine and dead‑letter:** repeatedly failing tasks go to quarantine; explicit, evidence‑rich replay | Quarantine tests pass |

### P3 — Application State Correctness (Weeks 7‑9)

**Goal:** Ensure applications never create duplicate external submissions. (References Plan1 §5‑7)

| ID | Task | Verification |
|----|------|-------------|
| P3.1 | **Formal state machine:** define complete application state machine (DISCOVERED→NORMALIZED→DEDUPLICATED→ENRICHED→MATCHED→SHORTLISTED→PREPARING→APPROVAL_PENDING→SUBMITTING→VERIFYING→SUBMITTED/FAILED/QUARANTINED) | State transition validation |
| P3.2 | **Idempotency keys:** all side‑effecting operations carry idempotency key | Duplicate submission rejected |
| P3.3 | **Durable human approval:** create `ApprovalRequest` entity (id, task_id, action, risk_level, proposed_arguments, evidence, policy_reason, expires_at, requested_at, decided_at, decided_by, decision, modified_arguments) | Approval workflow end‑to‑end |
| P3.4 | **Unknown state as first‑class:** submission_unknown, verification_unknown, provider_unknown, browser_unknown | Unknown states trigger reconciliation, not blind retry |
| P3.5 | **Submission reconciliation:** after submission, verify confirmation; ambiguous state stays SUBMISSION_UNKNOWN | Reconciliation tests pass |
| P3.6 | **Idempotency audit:** audit all side‑effecting operations to ensure idempotency | Audit report passes |

### P4 — Browser & Adapter Reliability (Weeks 9‑12)

**Goal:** Make browser automation reliable, expand ATS coverage. (References Plan1 §8, Plan3 AR‑1/AR‑2)

| ID | Task | Verification |
|----|------|-------------|
| P4.1 | **Browser session manager:** BrowserSessionManager + BrowserPool + ProfileStore + SessionPersistence | Session lifecycle tests |
| P4.2 | **Named actions:** abstract browser actions into named operations (navigate, fill form, submit, verify) | Action tests |
| P4.3 | **Selector registry + healing:** `src/jobot/stealth/selectors.py` – central dict (site → step → [candidate locators]), multi‑locator fallback on failure, healing log | Drift simulation tests pass |
| P4.4 | **Evidence capture:** risky browser actions capture – before/after screenshots, DOM snapshots, action, arguments, result, verification, trace ID, application ID | Evidence tests |
| P4.5 | **CAPTCHA boundary:** detect CAPTCHA and escalation path (human solver or alternate method) | CAPTCHA tests |
| P4.6 | **Site health & circuit breaker:** site blocking → circuit breaker → health incident → quarantine → alternate source / human action | Circuit breaker tests |
| P4.7 | **cxs‑API adapter family:** extract `CxsApiAdapter` base from `workday.py`; implement WorkableAdapter, RecruiteeAdapter, TeamtailorAdapter, BambooHrAdapter | New family tests; workday tests unchanged |
| P4.8 | **Direct API apply:** GreenhouseAdapter (Harvest API), LeverAdapter (Postings API), AshbyAdapter, SmartRecruitersAdapter | API submission tests |

### P5 — AI Reliability & Evaluation Platform (Weeks 12‑14)

**Goal:** Make AI outputs reliable, measurable, and traceable. (References Plan1 §10‑12, §22)

| ID | Task | Verification |
|----|------|-------------|
| P5.1 | **LLM streaming implementation:** implement `stream()` for all 6+ providers – Gemini, OpenAI, Anthropic, OpenAICompat (Groq, Together, OpenRouter, Ollama, vLLM), Mistral, Cohere | `jobot qa "Tell me about yourself" --stream` renders incrementally |
| P5.2 | **Typed LLM contracts:** structured output schemas; Pydantic models for all LLM interactions | Schema validation tests |
| P5.3 | **Prompt registry + versioning:** `prompts/` directory structure (application/fit_evaluation/v1.yaml etc.); record prompt_id, prompt_version, model, provider, temperature per model call | Prompt versioning traceable |
| P5.4 | **Capability‑aware routing:** routing considers Capability, Quality, Cost, Latency, Availability, Historical success, not just provider order | Routing tests |
| P5.5 | **Cost ledger:** `llm_calls`, `budgets`, `budget_reservations`, `provider_health`, `model_capabilities`, `routing_decisions` tables | Cost tracking tests |
| P5.6 | **Candidate truth system:** `CandidateFact` entity (fact_id, category, value, source, evidence, confidence, valid_from, valid_until) – generated application material must be grounded in candidate facts | Fact‑grounding tests |
| P5.7 | **Independent reviewer:** resume and cover letter generation followed by independent reviewer (catches unsupported claims, keyword stuffing, formatting failure, contradictions) | Reviewer tests |
| P5.8 | **Evaluation platform:** datasets, trajectory recorder, eval runner, baseline comparator, regression detector, security corpus, failure corpus | Every release can demonstrate whether agent quality improved or regressed |

### P6 — Production Artifacts & Release Engineering (Weeks 14‑17)

**Goal:** Build production artifacts for all distribution channels. (References plan4 R2)

| ID | Task | Verification |
|----|------|-------------|
| P6.1 | **PyPI trusted publishing:** `publish.yml` switch to `trusted‑publishing` (id‑token) + environment `pypi` | `twine check` clean; dry‑run to TestPyPI |
| P6.2 | **Docker publishing:** GHCR release workflow (amd64+arm64 manifests); `docker compose` smoke test in CI; tags `1.0.0` + `latest` | Multi‑arch images pull and run on both platforms; SBOM attached |
| P6.3 | **Desktop CI builds:** new `desktop.yml` – windows‑latest (NSIS+MSI), macos‑latest (DMG), ubuntu (AppImage+deb) via `npm run tauri:build`; `cargo check` as a CI gate job | Artifacts uploaded on tag; installers launch on clean VMs |
| P6.4 | **Real icon set:** design/commit an SVG; `npm run tauri icon` generates full suite | Icons render in CI‑built artifacts |
| P6.5 | **Auto‑update:** `tauri‑plugin‑updater` + generated signing keys; endpoints → GitHub Releases | Dev machine applies a staged dummy update |
| P6.6 | **Code signing (Windows):** SignPath OSS free tier → Authenticode signing in CI | Signed MSI/EXE passes `signtool verify` |
| P6.7 | **Code signing (macOS):** decision recorded – defer for v1; document Gatekeeper workaround (right‑click open, `xattr -dr com.apple.quarantine`) | Decision in `decisions.md` |
| P6.8 | **CSP hardening:** replace `"csp": null` with restrictive default (script‑src 'self'; style‑src 'self' 'unsafe‑inline'; connect‑src 'self' ipc: http://ipc.localhost) | `tauri:dev` + `tauri:build` run clean; no console CSP violations |
| P6.9 | **Capability re‑audit:** replace `args: true` with regex allowlist (`^sidecar$`, `^--[a-zA-Z0-9-]+(=.*)?$`) for spawn and execute | Capability validation passes |
| P6.10 | **Release pipeline assembly:** single `release.yml` orchestrating P6.1‑P6.3, attaching SBOMs + provenance attestation | One tag produces wheel + images + installers + SBOMs |

### P7 — Control Plane / GUI Completion (Weeks 17‑20)

**Goal:** Make the Tauri GUI the operational control plane. (References Plan1 §20)

| ID | Task | Verification |
|----|------|-------------|
| P7.1 | **Dashboard view** – active work, pending approvals, failures, daily applications, costs, top matches | Dashboard renders live data |
| P7.2 | **Task inspector** – status, owner, attempts, dependencies, current phase, evidence, logs, cost | Task inspector shows full info |
| P7.3 | **Approval inbox** – WHAT, WHY, RISK, EVIDENCE; [Approve], [Edit], [Reject], [Defer] | Approval workflow end‑to‑end |
| P7.4 | **Evidence viewer** – job, fit, resume, cover letter, questions, submission state, screenshots, verification | Evidence accessible |
| P7.5 | **Trace viewer** – Goal → Task → Model call → Tool call → Browser action → Policy evaluation → Approval → Verification → Artifact | Traces navigable |
| P7.6 | **Cost dashboard** – daily/weekly/monthly LLM spend by provider and task type | Cost data in GUI |
| P7.7 | **Incident dashboard** – what happened, timeline, affected applications, root cause, current mitigation, recommended fix | Incidents visible |
| P7.8 | **Kanban tracker** – stage columns (applied→interviewing→offer→rejected); drag between stages | Kanban functional |
| P7.9 | **Sidecar supervision:** GUI auto‑respawns on sidecar crash/exit; EOF and stdin backpressure handling; Windows process‑tree kill on GUI exit; pid‑file/lock against double‑run | Unit tests + manual kill test |
| P7.10 | **GUI E2E:** `tauri‑driver` + WebDriver tests (boot, discover via mock_ats, apply dry‑run, approve, dashboard render) | E2E suite green in CI |

### P8 — Capability Expansion (P0 Features) (Weeks 20‑24)

**Goal:** Deliver P0 features for v1.0.0. (References Plan3 §C.3)

| ID | Feature | Implementation Steps | Verification |
|----|---------|----------------------|-------------|
| P8.1 | **F‑01 Kanban + funnel** | Extend `tracker_stats` → `{funnel: {applied, interviewing, offer, rejected}, conversion_rates, by_site}`; new RPC `applications_by_stage`; Dashboard.jsx add stage columns | Sidecar + component tests |
| P8.2 | **F‑02 Autofill + answer bank** | Persist `form_field_memory` as `answer_bank` table; `fill_form` consults bank before LLM; RPC `answer_bank_list/upsert/delete`; new `Answers.jsx` view | Answer bank tests |
| P8.3 | **F‑03 Selector healing surfaced** | AR‑2 lands registry; sidecar `diagnostics` RPC exposes healing events; Settings view shows "browser health" | Diagnostics tests |
| P8.4 | **F‑04 ATS family expansion** | AR‑1 lands; registry + career_sites.yaml entries; `list_sites` shows new sites; Discover view selects them | Hermetic tests + one live opt‑in check |
| P8.5 | **F‑05 Follow‑up automation** | `outreach/` gains follow‑up generator; schedule follow‑ups per application; RPC `followups_list/create/cancel`; GUI "Follow‑ups" section; opt‑in flag `followups.enabled` | Follow‑up tests |
| P8.6 | **F‑06 Export/import** | `jobot export --format csv|json` + `import` (validation + dedup); RPC `export_data`; Settings view button → save dialog | Round‑trip tests |
| P8.7 | **F‑07 ATS score in GUI** | Reuse `documents/ats.py` via RPC `ats_score(pdf_path)`; resume variant selection in Apply view | ATS score tests |
| P8.8 | **F‑08 Answer bank UI** | P8.2 view + keyword search + dedupe | UI tests |
| P8.9 | **F‑10 Apply‑method classification** | `classify_apply_method(job)` in discovery (auto=known ATS+forms, manual=linkedin unless opted, email=mailto listings, redirect=external ATS); per‑posting method shown in Discover/Apply views | Classification tests |
| P8.10 | **F‑23 Job clipping** | Manual add from any URL to tracker | Clipping tests |

### P9 — Telemetry, Privacy & Documentation (Weeks 24‑26)

**Goal:** Establish telemetry, privacy guarantees, and comprehensive documentation. (References plan4 R4‑R5)

| ID | Task | Verification |
|----|------|-------------|
| P9.1 | **Crash reporting (Sentry):** opt‑in Sentry SDK (Python core + JS/Rust shell); redaction layer (profile identity, API keys, company/job URLs, evidence paths); consent in GUI onboarding + `jobot config set telemetry.enabled true|false`; `JOBOT_TELEMETRY=off` kill switch | Redaction unit tests; end‑to‑end test report |
| P9.2 | **Anonymous usage analytics:** task counts, success/failure rates, cost per run, version – no application data; opt‑in same switch | Payload schema documented; test asserts no PII fields |
| P9.3 | **`docs/privacy.md`:** exactly what is collected, when, how to disable, retention (30 days, no raw payload storage) | Doc reviewed against code; test enforces schema match |
| P9.4 | **Data hygiene:** `jobot purge` command (delete applications/evidence/logs per flags); retention defaults; evidence cleanup on uninstall path | Purge tests pass |
| P9.5 | **Health report:** `jobot doctor` gains version/env/degradation flags machine‑readable (`--json`) for support triage | `doctor --json` schema documented + tested |
| P9.6 | **Docs site:** VitePress – setup, CLI reference, GUI guide, adapters, security, telemetry, FAQ; CI builds site, publishes to GitHub Pages | Site builds clean; links checked |
| P9.7 | **Governance files:** `SECURITY.md` (vulnerability reporting + PGP, glib risk register, telemetry privacy pointer), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `FUNDING.yml`, issue templates, PR template, `CODEOWNERS` | Files render on GitHub |
| P9.8 | **Maintainer runbook:** local gates, release process checklist, branch/tag policy, hotfix path | Runbook executed in a dry‑run release |
| P9.9 | **README overhaul:** badges (CI/coverage/license/PyPI), quickstart (pip/Docker/desktop), GUI screenshots, architecture diagram, FAQ, sponsorship links | README renders; quickstart verified in fresh venv |
| P9.10 | **License hygiene:** add copyright holder line to LICENSE; audit headers (AGPL core, MIT adapters – correct claims or simplify README); add NOTICE if needed | `reuse lint`‑style audit report |
| P9.11 | **CHANGELOG.md** (Keep a Changelog) backfilled from worklog (Phases 0‑6) + `Unreleased` section | Markdown lint passes; entries traceable to worklog rows |

### P10 — Release & Launch (Weeks 26‑28)

**Goal:** Release v1.0.0 and establish community momentum. (References plan4 R5.3‑R5.5)

| ID | Task | Verification |
|----|------|-------------|
| P10.1 | **Community ops:** stale‑bot, label taxonomy, issue triage automation, public roadmap page (from queues/now.md) | Bot config live; roadmap page renders from queues |
| P10.2 | **Release candidate:** run full release pipeline; all gates pass | RC artifacts downloadable |
| P10.3 | **v1.0.0 tag:** tag `v1.0.0` → release pipeline → finalise CHANGELOG | Release published |
| P10.4 | **Launch announcement:** GitHub release + sponsorship call; live‑adapter status honestly documented in release notes (opt‑in, unvalidated on dev machine) | Release published; artifacts verifiably downloadable |
| P10.5 | **Post‑launch roadmap:** rewrite momentum queues into post‑1.0 roadmap (docs site content expansion, localization defer, multi‑machine coordination, SaaS exploration notes) | Queues updated; next milestone defined |

---

## Part V: Repository Hygiene & Cleanup

### 5.1 File Cleanup

| File/Directory | Action | Rationale |
|----------------|--------|-----------|
| `Plan1.pdf` | Move to `docs/` | Keep root clean |
| `.env` | Verify in `.gitignore`; rotate keys if committed | Security |
| `queues/improve.md` | Rewrite after reconciliation with code | Stale claims |
| `gui/src‑tauri/target/` | Add to `.gitignore` | Build artifacts |
| `__pycache__/`, `*.pyc` | Add to `.gitignore` | Python cache |
| `.coverage.*`, `htmlcov/` | Add to `.gitignore` | Coverage artifacts |
| `*.p12`, `*.pem`, `*.key` | Add to `.gitignore` | Key files |
| `.venv/`, `venv/` | Add to `.gitignore` | Virtual environments |
| Unused scripts | Audit and delete or archive | Reduce clutter |

### 5.2 Dependency Cleanup

| Action | Verification |
|--------|--------------|
| Remove unused `black` (ruff handles formatting) | `pip list` does not show black |
| Audit `jobspy` – the only undeclared import, deliberate (pins numpy==1.26.3; `--no‑deps` recipe in SETUP.md; import‑guarded) | Documented |
| Add `tests/test_imports.py` – import every src module with base install (no extras) | Guards undeclared‑deps regressions |

### 5.3 Git Ignore Update

Add to .gitignore

.venv/
venv/
*.p12
*.pem
.key
.coverage.
htmlcov/
pycache/
*.pyc
gui/src-tauri/target/
*.log
*.db-journal
text


---

## Part VI: Refactoring & Performance Optimisation

### 6.1 Codebase Organisation Refactoring

**Goal:** Organise the codebase into a clear layered architecture while maintaining backward compatibility. (References Plan1 §31)

**Target Structure:**

src/jobot/
├── core/ # Core primitives (no external deps)
│ ├── events/ # Event ledger
│ ├── state/ # State management
│ ├── tasks/ # Task graph
│ ├── workflows/ # Workflow engine
│ └── errors/ # Error hierarchy
│
├── control/ # Control plane
│ ├── goals/ # Goal management
│ ├── approvals/ # Approval workflows
│ ├── budgets/ # Budget tracking
│ ├── trust/ # Trust scores
│ ├── policies/ # Policy engine
│ └── incidents/ # Incident management
│
├── execution/ # Execution layer
│ ├── workers/ # Worker management
│ ├── leases/ # Task leases
│ ├── sandbox/ # Sandboxed execution
│ ├── browser/ # Browser automation
│ └── tools/ # Tool execution
│
├── ai/ # AI layer
│ ├── router/ # Model routing
│ ├── providers/ # Provider adapters
│ ├── prompts/ # Prompt registry
│ ├── profiles/ # Agent profiles
│ └── evaluation/ # Evaluations
│
├── memory/ # Memory layer
│ ├── semantic/ # Semantic memory
│ ├── episodic/ # Episodic memory
│ ├── procedural/ # Procedural memory
│ └── retrieval/ # Retrieval
│
├── career/ # Career domain
│ ├── matching/ # Job matching
│ ├── scoring/ # Scoring
│ ├── market/ # Market intelligence
│ ├── networking/ # Networking
│ └── interview/ # Interview preparation
│
├── applications/ # Application domain
│ ├── state_machine/ # State machine
│ ├── preparation/ # Preparation
│ ├── submission/ # Submission
│ └── verification/ # Verification
│
├── adapters/ # Adapters
│ ├── ats/ # ATS adapters
│ ├── boards/ # Job board adapters
│ └── browser/ # Browser adapters
│
├── documents/ # Document generation
│ ├── resume/ # Resume
│ ├── cover_letter/ # Cover letter
│ ├── pdf/ # PDF generation
│ └── ats/ # ATS scoring
│
├── observability/ # Observability
│ ├── tracing/ # Tracing
│ ├── metrics/ # Metrics
│ └── logging/ # Structured logging
│
├── plugins/ # Plugin system
│
├── cli/ # CLI commands (split)
│ ├── apply.py
│ ├── scrape.py
│ ├── resume.py
│ ├── interview.py
│ ├── tracker.py
│ ├── config.py
│ └── admin.py
│
└── gui/ # GUI sidecar bridge
└── sidecar.py
text


**Refactoring Strategy:** Incremental. Do not perform a single massive directory rewrite.

### 6.2 Performance Optimisations

| Area | Optimisation | Target |
|------|--------------|--------|
| **Import time** | Lazy imports; load heavy modules on demand | `jobot --help` < 500ms |
| **LLM calls** | Cache embeddings; batch requests; cheaper models for classification | 50% reduction in LLM cost |
| **Browser startup** | Browser pooling; warm sessions; reuse profiles | Startup < 2s |
| **Database** | Query optimisation; index addition; WAL checkpoint tuning | Queries < 50ms |
| **Memory** | Stream large responses; paginate artifacts; memory compaction | Memory < 512MB |
| **Parallelism** | Fan‑out independent tasks; batch API requests | 2× throughput |

### 6.3 Code Quality Improvements

| Action | Verification |
|--------|--------------|
| Split 1749‑line `cli/main.py` into 7 submodules | All 25+ CLI commands work identically |
| Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` | No Python 3.12+ deprecation warnings |
| Replace all `except Exception: pass` with explicit logging | `grep -r "except.*pass" src/` returns zero |
| Add `structlog` for structured JSON logging | Logs output in JSON format |
| Add request ID / correlation ID propagation across async calls | Trace correlation |
| Add `bandit` (Python security linter) to CI | `bandit -r src/` passes |
| Add `pip‑audit` to CI | `pip‑audit` passes |

### 6.4 Test Coverage Expansion

| Action | Target |
|--------|--------|
| Add `pytest‑cov` enforcement: fail CI if coverage drops below 70% | Coverage ≥ 75% |
| Write tests for untested modules: `digest/`, `notify/`, `outreach/`, `scheduler/loop.py` | All modules tested |
| Add negative/error‑path tests for every adapter | Error handling tests |
| Add integration test for full apply saga (mock ATS end‑to‑end) | End‑to‑end test |
| Add property‑based tests (via `hypothesis`) for PII masker patterns | Property tests pass |
| Add failure injection suite | Circuit breakers open on injected failures |
| Add soak tests: 1000‑iteration sidecar loop (memory leak check) | RSS bounded (±10%), DB growth linear, 0 crashes |

---

## Part VII: Decision Log

| # | Decision | Default | Rationale |
|---|----------|---------|-----------|
| D‑1 | `infer_site()` unknown URLs | Raise explicit `ValueError` instead of silently defaulting to `greenhouse` | Prevents misrouting |
| D‑2 | vite upgrade | Major upgrade `5.4.21 → 8.2.1` | Only clean fix |
| D‑3 | glib GHSA‑wrw7‑89jp‑8q8g | Accepted as documented residual risk | No fix in tauri 2 tree |
| D‑4 | Execution order | W1→W2→W4→W7→W6→W5→W8→W9→W3→W10 | Dependency ordering |
| D‑5 | macOS notarisation | Defer for v1; document Gatekeeper workaround | Cost vs benefit |
| D‑6 | Windows signing | SignPath OSS tier; fallback = defer + documented SmartScreen caveat | Open‑source friendly |
| D‑7 | Auto‑update hosting | GitHub Releases | No custom server |
| D‑8 | Docs site generator | VitePress | Existing Node stack |
| D‑9 | Coverage floor | Measured current −2%, minimum 70% | Pragmatic |
| D‑10 | Sentry vs self‑hosted error intake | Sentry SaaS (free tier) for v1 | Quick start |
| D‑11 | Browser extension (F‑15) | Defer to post‑1.0; track interest first | XL effort, separate repo |
| D‑12 | Gmail watcher authentication | Gmail API OAuth (no IMAP password storage) | Security |
| D‑13 | ToS‑risk features (F‑19/20/21) | Ship only behind `JOBOT_ENABLE_RISKY=1` + per‑feature flags; default off; docs warn | Protect reputation |
| D‑14 | MCP mode scope | stdio first, SSE later | Progressive delivery |

---

## Part VIII: Risk Register & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R1 | LinkedIn detects Patchright and bans accounts | HIGH | CRITICAL | Session reuse, realistic delays, daily caps, human fallback, circuit breaker |
| R2 | JobSpy selectors break on board redesigns | MEDIUM | HIGH | Pin version, health‑check cron, alert on circuit breaker opening, fallback to direct API |
| R3 | LLM API rate limits during batch operations | MEDIUM | MEDIUM | Fallback chain, per‑provider circuit breaker, daily cost cap, local Ollama fallback |
| R4 | AGPL license deters enterprise adoption | LOW | MEDIUM | Dual‑license option, clear documentation of AGPL requirements |
| R5 | Patchright fork falls behind upstream Playwright | MEDIUM | MEDIUM | Monitor upstream, contribute patches back, maintain vanilla Playwright fallback |
| R6 | GUI development delays block v1.0 | MEDIUM | MEDIUM | CLI‑first release strategy; GUI is v1.1 if needed |
| R7 | Saga left in half‑applied state | LOW | HIGH | Compensating actions, per‑phase checkpoints, quarantine queue |
| R8 | PII leakage to LLM providers | LOW | CRITICAL | PII masker before all LLM calls (already implemented), audit logging |
| R9 | vite 8/rolldown breaks GUI build or vitest 4 changes behaviour | MEDIUM | HIGH | Build + tests run in P1.1 before proceeding; revert if unresolvable, then escalate (document residual) |
| R10 | CodeQL re‑scan flags new patterns after refactor | MEDIUM | MEDIUM | Fix incrementally; one‑change loops per AGENTS.md |
| R11 | `infer_site` ValueError breaks CLI/sidecar UX | MEDIUM | MEDIUM | Surface clean error message + `jobot list‑sites` guidance |
| R12 | Refactor churn vs 359‑test baseline | MEDIUM | MEDIUM | A.1 gated: full suite green after each AR‑*; feature work merged via branches, gates in CI |
| R13 | Live adapters unvalidated on dev machine | MEDIUM | MEDIUM | Hermetic tests everywhere; live opt‑in stays; release notes honest |
| R14 | P0 feature load delays v1.0.0 | MEDIUM | MEDIUM | P0 scope is 8 features; anything slipping moves to P1 with user approval |
| R15 | ToS‑flagged features harm reputation | MEDIUM | MEDIUM | Default‑off flags + docs + no volume blasting (F‑05 rate caps) |

---

## Part IX: Success Metrics

### 9.1 Release Criteria

| Criterion | Threshold |
|-----------|-----------|
| All Dependabot/CodeQL alerts closed | 0 open |
| `npm audit` | 0 vulnerabilities |
| `pip‑audit` | 0 vulnerabilities |
| pytest coverage | ≥ 75% |
| ruff + mypy strict | Pass |
| `jobot doctor` | Pass on macOS, Linux, Windows (WSL2) |
| 3 real LinkedIn Easy Apply submissions verified | Pass |
| GUI dashboard functional | Live data |
| README comprehensive | Badges, screenshots, quickstart, architecture |
| CHANGELOG, CONTRIBUTING, LICENSE present | Yes |
| Docker image published to GHCR | Yes |
| PyPI package published | Yes |
| Desktop installers (3 OS) | Signed (Windows) / documented (macOS) |

### 9.2 Post‑Launch Metrics

- v1.0.0 artifacts downloadable from all three channels; install‑to‑doctor ≤ 5 min on each OS
- CI green on every PR; coverage ≥ floor; audit jobs clean
- Telemetry opt‑in rate ≥ 10% with zero PII incidents
- First 30 days: ≥ 1 external contribution (issue/PR), sponsorship page live

---

## Part X: Documentation Generation Checklist

### 10.1 Required Documents

| Document | Status | Location |
|----------|--------|----------|
| `README.md` | To overhaul | Root |
| `CHANGELOG.md` | To create | Root |
| `SECURITY.md` | To create | Root |
| `CONTRIBUTING.md` | To create | Root |
| `CODE_OF_CONDUCT.md` | To create | Root |
| `FUNDING.yml` | To create | `.github/` |
| `docs/privacy.md` | To create | `docs/` |
| `docs/release‑policy.md` | To create | `docs/` |
| `docs/contracts.md` | Exists | `docs/` |
| `SETUP.md` | Exists | Root |
| `LICENSE` | To add copyright holder | Root |
| `NOTICE` | If needed | Root |
| Issue templates | To create | `.github/ISSUE_TEMPLATE/` |
| PR template | To create | `.github/` |
| `CODEOWNERS` | To create | `.github/` |
| `.editorconfig` | To create | Root |

### 10.2 Docs Site (VitePress)

docs/
├── .vitepress/
│ └── config.js
├── index.md
├── guide/
│ ├── getting‑started.md
│ ├── installation.md
│ ├── configuration.md
│ └── cli‑reference.md
├── gui/
│ ├── overview.md
│ ├── dashboard.md
│ └── settings.md
├── adapters/
│ ├── overview.md
│ ├── greenhouse.md
│ ├── lever.md
│ └── adding‑adapters.md
├── security/
│ ├── overview.md
│ └── privacy.md
├── telemetry/
│ └── overview.md
└── faq.md
text


---

## Part XI: Execution Protocol

### 11.1 Work Package Execution

Each work package follows:

1. **Plan** → understand requirements, design approach
2. **Implement** → write code, make changes
3. **Verify** → run tests, gates pass
4. **Document** → update worklog, queues, changelog
5. **Commit** → commit with descriptive message

### 11.2 Gates

At the end of every phase:

- `pytest` passes (359+ tests)
- `ruff check` passes
- `mypy` passes
- `vitest` passes
- `prettier` passes
- `npm audit` passes (high level)
- Worklog updated
- Queues updated

### 11.3 Branch Strategy

- `main` – production‑ready code
- `develop` – integration branch
- `feature/*` – feature branches
- `release/*` – release candidates
- `hotfix/*` – emergency fixes

### 11.4 Commit Convention

<type>(<scope>): <subject>

[body]

[footer]
text


Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `security`

---

## Part XII: Post‑Release Roadmap (v1.1+)

### P1 Features (v1.1.x)

- F‑09 Gmail/IMAP watcher → auto status update from recruiter emails
- F‑11 24/7 job matcher: scored recommendation digest on schedule
- F‑12 Interview calendar + scheduling view
- F‑13 Salary negotiation toolkit
- F‑14 Session recordings + phase screenshots in GUI evidence viewer
- F‑16 MCP server mode
- F‑17 Resume bank: versioned per‑job variants + diff view
- F‑18 Local‑first LLM path (Ollama) incl. vision captcha

### P2 Features (v1.2+)

- F‑15 Browser extension
- F‑19 LinkedIn follow‑up/connection automation (ToS – opt‑in)
- F‑20 Stealth/proxy rotation wiring (ToS – opt‑in)
- F‑21 Bulk batch‑apply with caps (ToS – opt‑in)
- F‑22 Interview question bank expansion
- F‑24 Community adapter/plugin gallery

### Architectural Enhancements (v2.0+)

- AR‑7 Event bus
- AR‑8 Plugin‑ify adapters
- AR‑9 MCP server mode
- AR‑10 Async conversion of hot paths
- AR‑11 Multi‑machine coordination scaffolding
- Multi‑profile support
- Resume PDF parsing/ingestion
- Enhanced job matching engine (embedding‑based)
- Conversational AI assistant
- Resume A/B testing framework
- LinkedIn profile analyser
- Terminal UI (TUI) enhancement
- HTML report generator
- Structured telemetry pipeline (OpenTelemetry)
- Trust level automation
- Budget & cost dashboard
- Audit log
- API server mode
- Homebrew / OS package managers
- Proactive job discovery agent
- Application outcome learning loop
- Multi‑language resume support
- Networking graph & referral tracking

---