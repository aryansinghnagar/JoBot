# JoBot: Master Architecture, Refactor, and Production Readiness Plan

**Version:** 1.0 · 2026-08-15  
**Status:** APPROVED-PENDING-EXECUTION  
**Target:** `v1.0.0` (Production Release)  
**Guiding Principles:** `AGENTS.md` — No fabrication, verification-first, file-based state, observable > clever, local-first/privacy-preserving, human-in-the-loop governance, idempotent submissions.  

This document represents the unified, comprehensive Master Plan for JoBot. It synthesizes all prior planning documents (Plans 1-5) into a conflict-free, sequentially optimized roadmap. The goal is to transform JoBot from a feature-complete prototype into a durable, verifiable, commercially viable, and autonomous career operating system.

---

## Part I: Project Hygiene & Documentation Generation

Before adding new capabilities, the repository must be brought to industry-standard open-source hygiene. All documentation and governance files must be generated and maintained as living artifacts.

### 1. Repository Hygiene & Governance
*   **License & Metadata:** Update `LICENSE` with the copyright holder line ("Copyright (C) 2026 JoBot contributors"). Migrate `pyproject.toml` to `license = "AGPL-3.0-only"` SPDX string. Add `[project.urls]`, `classifiers`, and `keywords`.
*   **Governance Files:** Create `SECURITY.md` (vulnerability reporting, PGP, glib residual risk register, telemetry privacy pointer), `CONTRIBUTING.md` (local gates runbook, release process), `CODE_OF_CONDUCT.md`, `FUNDING.yml`, `CODEOWNERS`, and issue/PR templates.
*   **Version Authority:** Create `scripts/sync_versions.py` to synchronize versioning across `pyproject.toml`, root `package.json`, `gui/package.json`, and `tauri.conf.json`. Establish `pyproject.toml` as the single source of truth.
*   **Changelog:** Backfill `CHANGELOG.md` (Keep a Changelog format) from `worklog.md` and create an `Unreleased` section.

### 2. Comprehensive Documentation Suite
*   **VitePress Docs Site:** Stand up a VitePress documentation site deployed via GitHub Pages. Include:
    *   CLI Reference (extracted from `SETUP.md`).
    *   GUI Guide and Architecture Diagrams.
    *   Adapters documentation (honestly reflecting live opt-in status).
    *   Security & Telemetry privacy docs (`docs/privacy.md`).
    *   Maintainer Runbook (release checklists, branch/tag policy, hotfix paths).
*   **README Overhaul:** Add CI/coverage/license badges, quickstart guides (pip/Docker/desktop), GUI screenshots, architecture diagram, FAQ, and sponsorship links.

---

## Part II: Codebase Cleanup & Dead Code Removal

Eliminate technical debt, stale artifacts, and unnecessary files to reduce cognitive load and minimize the attack surface.

### 1. File System & Git Hygiene
*   **Artifact Relocation:** Move `Plan1.pdf` to `docs/` to keep root directory clean. Keep planning `.md` files at the root as living documents.
*   **Gitignore Expansion:** Add `.venv/`, `*.p12`, `.coverage.*` to `.gitignore`.
*   **Secrets Sweep:** Verify `.env` is completely ignored. Run `gitleaks` across full git history to ensure no secrets were ever committed. Rotate any found keys immediately.
*   **Stale Queue Reconciliation:** Audit `queues/improve.md` against the codebase. Mark wired items (QAEngine, PolicyEngine, CircuitBreaker, TraceLogger, AlertDispatcher) as done. Reframe `now/next/blocked` around this Master Plan.

### 2. Dead Code & Dependency Pruning
*   **Remove Redundant Tools:** Remove `black` from dev dependencies (standardize on `ruff format`). Remove narrow `--select E,F --ignore E501,F401` ruff invocations; use pyproject defaults.
*   **Eliminate Stubs:** Remove all `NotImplementedError` stubs in `llm/providers.py` (addressed in Phase 1), `scrapers/ats.py`, and `adapters/linkedin.py` (addressed in Phase 3).
*   **Remove Silent Failures:** Eradicate `except Exception: pass` blocks across `storage/vault.py` and adapter fallbacks. Replace with explicit structured logging and metric emission.
*   **Deprecation Cleanup:** Remove `datetime.utcnow()` (replace with `datetime.now(timezone.utc)`). Fix `mypy` configuration to `python_version = "3.11"` (matching `requires-python >=3.11`).

---

## Part III: System Refactor & Optimization (Speed, Efficiency, Resource Minimization)

Refactor the project to minimize memory, compute, and processing overhead while maximizing throughput and reliability.

### 1. CLI Monolith Split
*   **Problem:** `cli/main.py` is 1,749 lines, making it hard to maintain and test.
*   **Action:** Split into subcommand modules: `cli/apply.py`, `cli/scrape.py`, `cli/resume.py`, `cli/interview.py`, `cli/tracker.py`, `cli/config.py`, `cli/admin.py`. Extract shared helpers to `cli/helpers.py`. Ensure `main.py` < 100 lines.

### 2. Async Hot Path Conversion
*   **Action:** Convert hot paths (scraping, browser orchestration, LLM streaming) to asynchronous execution. Create a sync-compat shim (`jobot.asyncx`) to keep the CLI synchronous and simple.
*   **Benefit:** Non-blocking I/O for network and browser calls, drastically reducing CPU idle time and improving application throughput.

### 3. Database & State Optimization
*   **SQLite WAL Tuning:** Optimize SQLite WAL configuration. Implement `PRAGMA wal_checkpoint` behavior to bound DB growth during long soak tests.
*   **Memory Management:** Use `tracemalloc` in soak tests to verify RSS is bounded (±10%) over 1,000-iteration sidecar loops. Prevent memory leaks in long-running GUI/sidecar sessions.

### 4. LLM Compute Economics
*   **Multi-Stage Job Matching:** Do not send every job through an expensive LLM.
    *   *Stage 1:* Deterministic filtering (location, visa, salary, title).
    *   *Stage 2:* Cheap semantic matching (lexical/embedding score).
    *   *Stage 3:* Structured LLM evaluation.
    *   *Stage 4:* Deep company/job research (only for shortlisted jobs).
*   **Capability-Aware Routing:** Route tasks to the cheapest capable model. Use nano-models for classification/tagging; reserve strong models for planning and adversarial checking.

---

## Part IV: The Master Architecture & Execution Plan (Phases 0-8)

This sequence transforms JoBot into a durable, production-grade agent platform.

### Phase 0: Security, CI, & Core Fixes
*Priority: Release-blocking. Must be completed before any feature work.*

*   **W1: npm Stack Upgrade:** Upgrade Vite `5.4.21 → 8.2.1` (closes high CVEs, drops vulnerable esbuild). Upgrade Vitest to `^4.1.10`, Tauri APIs to `^2.11.1`. Update CI node matrix to 20/22.
*   **W2: CodeQL URL Sanitization:** Rewrite `infer_site()` in `src/jobot/adapters/registry.py`. Replace substring matching with exact `urlsplit` netloc matching. Raise explicit `ValueError` for unknown URLs instead of defaulting to Greenhouse. Write adversarial tests (`greenhouse.io.attacker.com`).
*   **W3: Vault Hardening:** Create keyfiles with `os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)` to eliminate the chmod-after-write window. Use `O_NOFOLLOW` on POSIX to prevent symlink attacks. Refuse reading world-readable keyfiles.
*   **W4: Tauri/GUI Hardening:** Replace `"csp": null` with restrictive CSP (`script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' ipc: http://ipc.localhost`). Replace `args: true` in capabilities with regex allowlists for spawn/execute.
*   **W5: CI Hardening:** SHA-pin all GitHub Actions. Add `actionlint`, `pip-audit`, `npm audit --audit-level=high`, and `gitleaks` to a new `security-gates` job. Add `cargo` ecosystem to Dependabot. Switch PyPI publishing to trusted publishing (`id-token: write`).

### Phase 1: Durable Execution Core & State Correctness
*Priority: P0. The core production invariant: NO ACTION WITHOUT A STATE, NO STATE WITHOUT AN EVENT, NO COMPLETION WITHOUT VERIFICATION.*

*   **Durable Task Graph:** Replace the in-memory task graph dictionary with persistent DB entities (`Task`, `TaskAttempt`, `TaskLease`, `TaskEvent`, `TaskArtifact`). Implement atomic claiming at the database level using conditional updates.
*   **Event & Effect Ledger:** Introduce `events` (append-only audit log) and `ExternalEffect` tables. Record `idempotency_key`, `request_hash`, and `compensation_state` for all external side effects.
*   **Unknown States:** Implement `submission_unknown`, `verification_unknown`, `browser_unknown`, etc. Ambiguity must trigger reconciliation or quarantine, never blind retries.
*   **Durable Human Approval:** Make `PENDING_APPROVAL` a first-class persistent entity (`ApprovalRequest`). GUI, CLI, and MCP must consume the same model.
*   **Database Migrations:** Replace ad-hoc migration logic with versioned migrations (`schema_migrations`). Add `jobot db status/migrate/backup/restore/verify` commands.

### Phase 2: AI Reliability & LLM Economics
*Priority: P0. Ensure trustworthy candidate data and reliable AI generation.*

*   **LLM Streaming De-Stub:** Implement `stream()` for all 6+ providers (Gemini, OpenAI, Anthropic, OpenAICompat, Mistral, Cohere). Wire streaming into CLI and GUI for real-time token feedback.
*   **Candidate Truth System:** Create `CandidateFact` table (category, value, source, evidence, confidence). LLMs may propose facts, but cannot silently mutate authoritative profile truth. All generated materials must be grounded in candidate facts.
*   **Independent Reviewer:** Enhance the resume/cover-letter pipeline. The reviewer must independently catch unsupported claims, keyword stuffing, and formatting failures.
*   **Prompt Management:** Version prompts like code (`prompts/application/fit_evaluation/v1.yaml`). Record `prompt_id` and `prompt_version` for every model call.
*   **Layered Memory System:** Explicitly separate Hot (current task), Warm (preferences), Semantic (facts), Episodic (run history), and Procedural (workflows) memory.

### Phase 3: Core Pipeline & Adapter Completion
*Priority: P0. Complete the flagship user journey: scrape → tailor → apply → verify.*

*   **LinkedIn Easy Apply:** Implement using Patchright (stealth Playwright). Handle login session reuse, form-field detection, QAEngine dynamic answering, screenshot evidence, and human-in-the-loop preview before final submit.
*   **cxs-API Adapter Family:** Extract `CxsApiAdapter` base from `workday.py`. Implement `WorkableAdapter`, `RecruiteeAdapter`, `TeamtailorAdapter`, `BambooHrAdapter`.
*   **Direct API Apply:** Complete `GreenhouseAdapter`, `LeverAdapter`, `AshbyAdapter`, `SmartRecruitersAdapter` using public APIs to bypass browser overhead.
*   **Multi-Profile Support:** Remove hardcoded `profile_id="default"`. Add `--profile` flag to CLI. Update vault and DB schema to associate applications with named profiles.
*   **Resume PDF Ingestion:** Implement `ResumeParser` using `pdfminer.six` + LLM-assisted extraction. Add `jobot profile import-resume <path.pdf>`.
*   **Selector Registry & Healing:** Centralize DOM selectors in `src/jobot/stealth/selectors.py`. Implement multi-locator fallback and drift simulation tests.

### Phase 4: GUI Control Plane & User Surfaces
*Priority: P0. The interface is part of the intelligence of the system.*

*   **GUI as Control Plane:** Upgrade Tauri 2 app.
    *   *Home:* Active work, pending approvals, failures, daily quotas, costs.
    *   *Task/Application:* Status, saga state, form values, screenshots, verification, timeline.
    *   *Approval UX:* Show what, why, risk, evidence. Allow Approve/Edit/Reject/Defer.
    *   *Incident Dashboard:* What happened, root cause, affected apps, mitigation.
*   **Kanban Tracker & Funnel:** Visual pipeline (Applied → Interviewing → Offer → Rejected). Drag-and-drop stages via `tracker_move` RPC.
*   **Answer Bank UI:** Persist `form_field_memory` as `answer_bank` table. View/edit/reuse screening answers per question type.
*   **TUI Enhancement:** `jobot tui` using `textual` for power users (live scrape progress, cost tracker, keyboard shortcuts).
*   **HTML Reports:** Enhanced `TrackerRenderer` with Chart.js funnel visualization and export-to-PDF.

### Phase 5: Reliability, Verification & Observability
*Priority: P0. Make every action visible, auditable, and governable.*

*   **Failure Injection Suite:** Adapter timeouts, HTTP 500/429, malformed JSON, browser crashes, sidecar killed mid-RPC. Assert circuit breakers open and quarantine receives work.
*   **Soak Tests:** 1,000-iteration sidecar loop verifying memory bounds, SQLite WAL growth, and 0 crashes.
*   **Evaluation Platform:** Make evals a release gate. Add datasets, trajectory recorder, regression detector, and security corpora (prompt injection, malicious URLs).
*   **Structured Telemetry:** Opt-in Sentry SDK with strict redaction (profile identity, API keys, URLs, evidence paths). Kill switch via `JOBOT_TELEMETRY=off`.
*   **`jobot doctor` Expansion:** Test runtime, security, browser (Patchright/Chromium), documents (LaTeX, pdftotext), AI providers, adapters, and control plane. Support `--json` output.

### Phase 6: Career Intelligence & Outcome Learning
*Priority: P1. The long-term differentiator. Transition from automation tool to career OS.*

*   **Outcome Learning Loop:** Track job → application → response → interview → offer. Use outcome data to refine match scoring and identify successful resume variants.
*   **Proactive Job Discovery Agent:** Always-on background scanner. Alert on high-match jobs. Auto-save and pre-tailor materials.
*   **Post-Apply Follow-ups:** Schedule and draft follow-up emails to recruiters. Rate-capped, grounded, and tone-capped.
*   **Salary & Market Intelligence:** Benchmark data and negotiation scripts per level.
*   **Networking Graph:** Track contacts, companies, referrals. Suggest warm introductions.

### Phase 7: Advanced Capabilities & Autonomous Expansion
*Priority: P1/P2. Push the boundaries of autonomous job application.*

*   **MCP Integration:** Expose JoBot as an MCP server (`jobot mcp`). Tools: `search_jobs`, `rank_jobs`, `prepare_application`, `request_application_approval`, `get_application_evidence`.
*   **API Server Mode:** `jobot serve` (FastAPI) exposing REST endpoints (`/scrape`, `/apply`, `/tracker`). Enables headless deployment and webhooks.
*   **Browser Extension:** Manifest V3 Chrome extension. "Apply with JoBot" button injected on job boards. Communicates with local `jobot serve`.
*   **Sandbox Execution:** Isolate untrusted plugins/generated code (restricted subprocess → container sandbox).
*   **Plugin Security:** Manifest → source/hash verification → permissions (deny-by-default) → dependency scan → install.
*   **Self-Improvement Loop:** Identify gaps (skill, tool, policy, prompt, memory) → improvement proposal → sandbox branch → eval → baseline comparison → gate → promote or discard. Never permit unrestricted production self-modification.

### Phase 8: Production Release Engineering
*Priority: P0. Ship v1.0 to the public.*

*   **Distribution Artifacts:**
    *   *PyPI:* Trusted publishing, `twine check` clean.
    *   *Docker:* GHCR multi-arch (amd64+arm64), `docker compose` smoke test in CI.
    *   *Desktop:* Tauri builds for Windows (NSIS+MSI), macOS (DMG), Linux (AppImage+deb). Auto-updater via GitHub Releases.
*   **Code Signing:** Windows via SignPath OSS tier. macOS: defer notarization ($99/yr) for v1, document Gatekeeper workaround.
*   **Local Gates Script:** `scripts/gates.ps1` and `scripts/gates.sh` (pytest, ruff, mypy, vitest, prettier, npm audit, sync_versions check).
*   **Launch Checklist:** Tag `v1.0.0` → release pipeline → finalize changelog → announcement. Submit to Hacker News, r/Python, Product Hunt.

---

## Part V: Success Metrics & Final Verification

By the time this Master Plan is implemented, JoBot must satisfy the following definition of done for `v1.0.0`:

1.  **Functional:** One end-to-end job application (discover → tailor → apply → verify) is durable, re-coverable, and observable under failure. Process death/resume does not duplicate external side effects.
2.  **Reliability:** 359+ pytest tests green, vitest 18/18, ruff/mypy clean. Failure injection suite passes. Soak test shows 0 crashes and bounded RSS.
3.  **Security:** `npm audit` 0 vulnerabilities, `pip-audit` clean, `gitleaks` 0 findings, CodeQL 0 alerts, `actionlint` clean. Vault keyfile hardened. CSP restrictive.
4.  **Packaging:** Wheel/sdist install cleanly. Docker image pulls and runs. Desktop installers launch on clean VMs. `jobot doctor` passes on macOS, Linux, Windows.
5.  **Community:** Docs site live. VitePress guides render correctly. Governance files present. `README` has quickstart and badges.
6.  **Economics:** LLM spend tracked. Capability-aware routing ensures cheap models are used for classification.

---

## Appendix: Execution Protocol

*   **One-change eval loops:** Feature branches + PRs. No giant prompt surgery.
*   **File-based state:** `queues/`, `plan.md`, `tasks.md`, `worklog.md` updated *during* execution, not just at the end.
*   **Honest Adapters:** Live opt-in (`JOBOT_RUN_LIVE_BROWSER=1`) stays opt-in. Release notes state exactly what was validated vs. hermetic only.
*   **Gates before tags:** No release without the full gate suite green.