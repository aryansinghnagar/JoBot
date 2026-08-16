# JoBot Master Plan — Refactor, Production Readiness & Competitive Feature Backlog

**Version:** 1.0 · 2026-08-15 · Status: APPROVED-PENDING-EXECUTION
**Target:** production-grade, released, commercially adopted open-source product (`v1.0.0`+)
**Guiding principles:** AGENTS.md (repo root) — no fabrication, verification-first, file-based state, one-change eval loops, momentum queues, open standards over lock-in.

## 1. Baseline (verified 2026-08-15)

- Release 2.0 tagged/pushed: honest adapters (lever, greenhouse, ashby, smartrecruiters, naukri, linkedin, workday, 8 JobSpy boards), 22-method JSON-RPC sidecar, Tauri 2 + React GUI (5 views), shared doctor
- Gates: pytest 359/13, ruff+mypy clean (116 files), vitest 18/18, prettier clean; CI (3-OS × 2-Py, npm, SBOM+provenance, CodeQL, Dependabot, PyPI publish)
- Ops built-ins: saga 12-phase ASP, quarantine, traces, backup/migrate, scheduler + caps, keyring+Fernet secrets, 27 modules / 116 files in `src/jobot`
- Existing plans: `plan4.md` (R1–R5, 37 tasks) — this master plan **references** it (Part B) rather than duplicating

## 2. Architecture Assessment (input to refactor)

**Strong:** adapter registry + honest per-site adapters; saga orchestrator with DoD gates; typed contracts doc; doctor; hermetic test culture (359 tests, fake browser/HTTP); no-fabrication invariant enforced by tests; sidecar RPC with injectable deps; GUI SSR-safe views.

**Weak / tech debt:**
| Area | Issue |
|---|---|
| Browser layer (`stealth/`) | Selectors hard-coded per adapter; no central registry, no healing, no drift simulation tests; `proxy.py` and `captcha.py` vision path unwired |
| Adapter families | Workday cxs-API pattern is bespoke; workable/icims/sap/ultipro need generalization (same API shape) |
| Memory system | `form_field_memory` tier not persisted/wired (8-tier system partially built) |
| `obs/` | Alerts/tracing exist; no event bus; AlertDispatcher not wired to scheduler/GUI |
| `improve.md` | Stale (9 items, most already wired) — needs reconciliation |
| Contracts | Adapter protocol duck-typed; no runtime schema validation at phase boundaries |
| GUI | No E2E, no Kanban/CRM view, no settings for telemetry/backup |
| Multi-machine / integration | No MCP surface, no event-driven extension points for external tools |

## 3. Part A — Refactor Program

### A.1 Incremental refactor track (weeks 1–6, low regression risk — "both, phased" step 1)

| ID | Refactor | Steps | Verify |
|---|---|---|---|
| AR-1 | **cxs-API adapter family**: extract `CxsApiAdapter` base from `workday.py` (POST `/wday/cxs/{tenant}/{site}/jobs` + `/jobPosting/{id}`, html.unescape, paging); implement `WorkableAdapter` (`/api/v1/jobs`), `RecruiteeAdapter`, `TeamtailorAdapter`, `BambooHrAdapter` (public JSON feeds); keep workday behavior byte-identical | 1) Move cxs HTTP+parse into `src/jobot/adapters/cxs_api.py`; 2) subclass per site w/ config keys `adapters.<site>.tenant`; 3) registry entries + `career_sites.yaml` fingerprints; 4) hermetic tests per adapter | pytest ≥ 359 + new family tests; workday tests unchanged green; live opt-in for 1 new site |
| AR-2 | **Selector registry + healing**: `src/jobot/stealth/selectors.py` — central dictionary (site → step → [candidate locators]), multi-locator fallback on failure, healing log; refactor naukri/workday/linkedin submit/verify to use it; add `tests/test_selector_healing.py` (simulated DOM drift) | 1) Schema + registry YAML; 2) resolver with retry-on-alternate; 3) migrate adapters; 4) drift simulation tests | Healing tests green; no adapter behavior regression |
| AR-3 | **Wire unwired subsystems**: `ProxyManager` into browser context init (config `scraper.jobspy.proxy_list` + `adapters.*.proxy`); `CaptchaSolver` vision path (multimodal bytes → LLM vision); persist `form_field_memory` tier (db table + reuse in `fill_form`) | Follow `improve.md` items 7/8/9; tests per subsystem | New tests green; gates clean |
| AR-4 | **Boundary schemas**: pydantic models for adapter I/O (JobPosting, ApplicationResult, SubmitOutcome) validated in registry + ASP phases; runtime validation errors → quarantined, never silent | Add `src/jobot/models/adapter_schemas.py`; wire into `registry.py` + `pipeline.py` | Validation tests; contracts.md updated |
| AR-5 | **Sidecar supervision + GUI resilience**: auto-respawn, EOF/backpressure, process-tree kill, double-run lock (from plan4 R3.1 — moved earlier since it unblocks GUI E2E) | As plan4 R3.1 | Unit tests + manual kill test |
| AR-6 | **Dead code + improve.md reconciliation**: audit `queues/improve.md` against code; remove/flag dead modules; update queues | `git grep` audit report; queues truthful | No stale claims |

### A.2 Deep restructure track (follow-on, weeks 8+ — "both, phased" step 2; gated on A.1 stability)

| ID | Restructure | Steps | Verify |
|---|---|---|---|
| AR-7 | **Event bus** in `obs/`: typed events (application.created, submit.succeeded, incident.opened, schedule.ran) + subscribers (alerts, telemetry, GUI push); replace direct calls in pipeline/runner | `events.py` + wire-ins; event log table | Event tests; alerts fire via bus |
| AR-8 | **Plugin-ify adapters**: adapter ABI (discover/submit/verify/fill_form) loadable via plugin manifest; registry auto-discovers installed adapter plugins | Extend `plugins/` with adapter kind; docs | Sample adapter plugin end-to-end |
| AR-9 | **MCP server mode**: `jobot mcp` — expose tools (discover, apply-dry-run, approve, tracker, digest, doctor) over Model Context Protocol; stdio + SSE; reuse sidecar method registry | `src/jobot/mcp/` adapter over sidecar handlers; MCP SDK dep (optional extra) | `jobot mcp` connects in a generic MCP client; tools callable |
| AR-10 | **Async conversion of hot paths** (scraping, browser orchestration) with sync-compat shim; keep CLI sync | Async facade `jobot.asyncx`; move scraping loop | Behavior-identical; perf bench ≥ 1.2× |
| AR-11 | **Multi-machine coordination scaffolding**: file-protocol task sync (hub-worker layout per AGENTS.md) + git-worktree isolation for parallel coding; no UI yet | `workflows/` harness docs + sync script | Two workers on same goal converge |

## 4. Part B — Production & Release Readiness

Carry forward **plan4.md** unchanged as the authoritative release track (R1 Foundation → R2 Artifacts → R3 Reliability → R4 Telemetry → R5 Launch). Deltas added here:

- **B-1:** GUI E2E (plan4 R3.6) now also covers Kanban + answer-bank views from Part C (P0 features land before E2E freeze)
- **B-2:** Release pipeline artifacts include MCP mode (`jobot mcp` extra) when AR-9 ships
- **B-3:** Telemetry events (plan4 R4.2) keyed to event bus (AR-7) once it exists
- **B-4:** Docs site (plan4 R5.1) gains the feature pages for all P0 shipped features
- **B-5:** Live validation budget: adapters remain opt-in; release notes state honestly what was validated on the dev machine vs CI hermetic only

## 5. Part C — Competitive Research & Feature Backlog

### C.1 Research sources

| Project | License | Observed features relevant to JoBot |
|---|---|---|
| Auto-Job-Applier-AI (2.3k★, Python) | MIT | AI resume customization per job, browser automation, board coverage |
| Simplify Jobs Bot (1.8k★, TS) | GPL-3.0 | LinkedIn automation; resilience patterns |
| Job Hunt Automator (1.2k★, Node) | Apache-2.0 | 50+ job boards coverage |
| ai-linkedin-easy-apply-agent | — | **UI Selectors System** (single source of truth DOM selectors), network-instability resilience |
| Browser Harness / browser-use / Intuned | MIT | **Self-healing selectors**, deterministic-core + AI-at-edges, managed auth sessions, batched jobs + retries, session recordings, stealth fleets |
| OpenClaw auto-job-applier skill | MIT | **Apply-method classification** (auto/manual/email/redirect), approval-list UX, preferences persistence |
| AutoApply (Electron+Flask) | MIT | CHANGELOG/CODEOWNERS hygiene, Playwright apply across 6 ATS |
| career-ops | MIT | Local-first via coding CLIs |
| ai-job-agent (10-agent) | MIT | Agent decomposition, alembic migrations, k8s (scaled-down ideas only) |
| Teal (commercial) | — | Unlimited ATS-friendly per-job resumes, bookmarking extension, match scoring, keyword optimization |
| Huntr (commercial) | — | Kanban CRM tracking, Gmail auto-tracking, contact/recruiter tracker, activity log, calendar + interview scheduling |
| Simplify (commercial) | — | Autofill across major ATS, auto-tracking post-submit, personalized recommendations |
| FastApply (commercial) | — | 150+ ATS, auto-pilot mode, 24/7 job matcher, custom screener answers |
| Jobscan (commercial) | — | Live ATS resume scanning |
| ApplyArc (commercial) | — | 18 AI tools incl. interview prep + salary negotiation, data export/deletion controls |
| LoopCV / LazyApply / Jobright (commercial) | — | Bulk apply batching, matched-position volume flows |

### C.2 Scored feature backlog (GUI-first; effort S/M/L/XL; value/fit 1–5; tier = priority)

**Legend:** tier P0 (ship for v1.0.0), P1 (1.0.x), P2 (opt-in/experimental, ToS-flagged where noted).

| ID | Feature | Source | Effort | Value | Fit | Risk | Tier |
|---|---|---|---|---|---|---|---|
| F-01 | GUI Kanban tracker + funnel analytics (applied→interview→offer conversion) | Huntr/Teal | L | 5 | 5 | none | P0 |
| F-02 | Form autofill generalization + persistent screening-answer bank | Simplify / own QAEngine | M | 5 | 4 | none | P0 |
| F-03 | Selector registry + healing (AR-2 surfaced in GUI diagnostics) | ai-linkedin-easy-apply / Browser Harness | M | 4 | 5 | none | P0 |
| F-04 | ATS family expansion: workable, recruitee, teamtailor, bamboohr (cxs-family, AR-1) | AutoApply/FastApply coverage | M | 4 | 5 | low | P0 |
| F-05 | Post-apply follow-up automation (draft + schedule follow-ups per application) | Huntr contact tracker | M | 4 | 4 | ToS(boards)/email | P0* |
| F-06 | Data export/import (CSV+JSON, per-application) in GUI + CLI | ApplyArc | S | 3 | 5 | none | P0 |
| F-07 | Live ATS score + per-job resume variants in GUI | Teal/Jobscan | M | 4 | 5 | none | P0 |
| F-08 | Screening answer bank UI (view/edit/reuse per question type) | Simplify gap | M | 4 | 4 | none | P0 |
| F-09 | Gmail/IMAP watcher → auto status update from recruiter emails | Huntr | L | 4 | 3 | none (OAuth) | P1 |
| F-10 | Apply-method classification per posting (auto/manual/email/redirect) | OpenClaw skill | S | 4 | 5 | none | P0 |
| F-11 | 24/7 job matcher: scored recommendation digest on schedule | FastApply | M | 4 | 4 | none | P1 |
| F-12 | Interview calendar + scheduling view | Huntr | M | 3 | 4 | none | P1 |
| F-13 | Salary negotiation toolkit (bands + negotiation scripts per level) | ApplyArc/Jobr | S | 3 | 4 | none | P1 |
| F-14 | Session recordings + phase screenshots in GUI evidence viewer | Browser Harness | M | 3 | 4 | none | P1 |
| F-15 | Browser extension (bookmark-from-any-board + autofill assist) | Teal/Simplify | XL | 4 | 2 | none (separate repo) | P2 |
| F-16 | MCP server mode (AR-9) | AGENTS.md open standards | M | 4 | 4 | none | P1 |
| F-17 | Resume bank: versioned per-job variants + diff view | Teal | M | 4 | 4 | none | P1 |
| F-18 | Local-first LLM path (Ollama) incl. vision captcha | browser-use local models | M | 3 | 4 | none | P1 |
| F-19 | LinkedIn follow-up/connection automation | Simplify/LoopCV | M | 3 | 3 | **ToS — opt-in** | P2 |
| F-20 | Stealth/proxy rotation wiring (ProxyManager) | browser-use stealth | M | 3 | 4 | ToS — opt-in | P2 |
| F-21 | Bulk batch-apply with caps (batch across boards) | LoopCV/FastApply | L | 3 | 3 | ToS — opt-in | P2 |
| F-22 | Interview question bank expansion (public datasets) | ApplyArc/Jobr | S | 2 | 4 | none | P2 |
| F-23 | Job clipping (manual add from any URL → tracker) | Teal | S | 3 | 5 | none | P1 |
| F-24 | Community adapter/plugin gallery (AR-8 enabled) | AutoApply ecosystem | L | 3 | 4 | none | P2 |

### C.3 Implementation steps per P0 feature (GUI-first; sidecar method + view named)

- **F-01 Kanban + funnel**: 1) `tracker_stats` extended → `{funnel: {applied, interviewing, offer, rejected}, conversion_rates, by_site}`; 2) new RPC `applications_by_stage`; 3) `Dashboard.jsx` → add stage columns (drag between stages via `tracker_move` RPC); 4) funnel chart (CSS/vanilla, no chart dep); 5) tests: sidecar + component.
- **F-02 Autofill + answer bank**: 1) persist `form_field_memory` (AR-3) as `answer_bank` table (question-hash → answer, source=profile|memory|llm); 2) `fill_form` consults bank before LLM; 3) RPC `answer_bank_list/upsert/delete`; 4) new `Answers.jsx` view; 5) tests.
- **F-03 Selector healing surfaced**: 1) AR-2 lands registry; 2) sidecar `diagnostics` RPC exposes healing events; 3) Settings view shows "browser health" (healing count, drift detections); 4) tests.
- **F-04 ATS family**: AR-1 lands; 1) registry + career_sites.yaml entries; 2) `list_sites` shows new sites; 3) Discover view selects them; 4) hermetic tests; 5) one live opt-in check.
- **F-05 Follow-up automation**: 1) `outreach/` gains follow-up generator (grounded, tone-capped); 2) schedule follow-ups per application (due-date + status); 3) RPC `followups_list/create/cancel`; 4) GUI "Follow-ups" section in Dashboard; 5) opt-in flag `followups.enabled`; 6) tests. *(F-05 carries the P0* ToS note: email follow-ups to recruiters only, rate-capped, no volume blasting.)*
- **F-06 Export/import**: 1) `jobot export --format csv|json` + `import` (validation + dedup); 2) RPC `export_data`; 3) Settings view button → save dialog (Tauri); 4) tests incl. round-trip.
- **F-07 ATS score in GUI**: 1) reuse `documents/ats.py` via RPC `ats_score(pdf_path)`; 2) resume variant selection in Apply view (per-job tailored PDF + score chip); 3) tests.
- **F-08 Answer bank UI**: F-02 view; plus keyword search + dedupe; tests.
- **F-10 Apply-method classification**: 1) `classify_apply_method(job)` in discovery (auto=known ATS+forms, manual=linkedin unless opted, email=mailto listings, redirect=external ATS); 2) per-posting method shown in Discover/Apply views; 3) policy `apply.method_override`; 4) tests.

## 6. Part D — Sequencing, Decisions, Risks

### D.1 Unified timeline (weeks)

| Weeks | Track | Work |
|---|---|---|
| 1–2 | R1 (prod) + AR-1/AR-3 | Foundation, versioning, gates; cxs-family + unwired subsystems |
| 3–4 | R2 (prod) + AR-2/AR-5 + F-03/F-04/F-10 | Artifacts pipeline; selector registry; GUI resilience |
| 5–6 | R3 (prod) + F-01/F-02/F-06/F-07/F-08 | Reliability + first P0 features land (GUI E2E covers them) |
| 7–8 | R4 (prod) + F-05/F-23 | Telemetry/privacy + follow-ups + clipping |
| 9–12 | R5 (prod) + P1 features + AR-7/AR-9 start | Launch v1.0.0; then deep-restructure track begins (AR-7 → AR-11) |

### D.2 New decisions (extend plan4 §6)

| # | Decision | Default |
|---|---|---|
| D7 | F-15 browser extension (XL effort, separate repo) | Defer to post-1.0; track interest first |
| D8 | F-09 Gmail watcher auth | Gmail API OAuth (no IMAP password storage) |
| D9 | F-19/20/21 ToS-risk features | Ship only behind `JOBOT_ENABLE_RISKY=1` + per-feature flags; default off; docs warn |
| D10 | MCP mode scope (F-16/AR-9) | stdio first, SSE later |

### D.3 Risks

| Risk | Mitigation |
|---|---|
| Refactor churn vs 359-test baseline | A.1 gated: full suite green after each AR-*; feature work merged via branches, gates in CI |
| Live adapters unvalidated on dev machine | Hermetic tests everywhere; live opt-in stays; release notes honest |
| P0 feature load delays v1.0.0 | P0 scope is 8 features; anything slipping moves to P1 with user approval |
| ToS-flagged features harm reputation | Default-off flags + docs + no volume blasting (F-05 rate caps) |
| Deep restructure (AR-7+) stalls core | Gated on post-1.0; one-change eval loop per AR-* |

### D.4 Success metrics (post-launch)

- v1.0.0 ships F-01..F-08, F-10, F-23; gates green; artifacts on all 3 channels
- GUI E2E covers P0 features; telemetry opt-in ≥ 10% with zero PII incidents
- ≥ 1 external contribution in first 30 days; docs site live

## 7. Execution Protocol

- Every task: plan → implement → verify (tests) → gates (pytest/ruff/mypy/vitest/prettier) → worklog + queues update
- Feature branches + PRs; one-change eval loops; no giant prompt surgery
- All research-driven claims marked with source; nothing adopted without local eval (per AGENTS.md external-intelligence loop)