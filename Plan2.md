# JoBot: Comprehensive Refactor & Production Readiness Plan

**Version:** 1.0 · 2026-08-15  
**Author:** Architecture Team  
**Status:** PLANNING — No implementation until explicitly approved  
**Guiding Document:** [`AGENTS.md`](./agents.md) (system doctrine & operating principles)

---

## Table of Contents

1. [Meta-Plan: Plan for the Plan](#1-meta-plan-plan-for-the-plan)
2. [Current State Audit](#2-current-state-audit)
3. [Competitive Landscape & Feature Intelligence](#3-competitive-landscape--feature-intelligence)
4. [Gap Analysis: JoBot vs Market](#4-gap-analysis-jobot-vs-market)
5. [Phase 1: Foundation Hardening](#5-phase-1-foundation-hardening)
6. [Phase 2: Core Pipeline Completion](#6-phase-2-core-pipeline-completion)
7. [Phase 3: Intelligence & Matching Layer](#7-phase-3-intelligence--matching-layer)
8. [Phase 4: User-Facing Surface & GUI](#8-phase-4-user-facing-surface--gui)
9. [Phase 5: Observability, Governance & Trust](#9-phase-5-observability-governance--trust)
10. [Phase 6: Production Infrastructure](#10-phase-6-production-infrastructure)
11. [Phase 7: Advanced Features & Differentiation](#11-phase-7-advanced-features--differentiation)
12. [Phase 8: Release Engineering & Launch](#12-phase-8-release-engineering--launch)
13. [Clarification Questions](#13-clarification-questions)
14. [Risk Register](#14-risk-register)
15. [Appendices](#15-appendices)

---

## 1. Meta-Plan: Plan for the Plan

### Planning Methodology

This plan is itself phased. Each section was produced by a distinct research activity:

| Planning Phase | Activity | Output |
|---|---|---|
| P0 — Doctrine Review | Read `AGENTS.md`, `PLAN.md`, `SETUP.md`, `docs/contracts.md` | Operating principles, frozen contracts, non-negotiable constraints |
| P1 — Codebase Audit | Analyze all 116 Python source files (~509 KB), 74 test files (~252 KB), CI/CD, GUI | Module-by-module gap map, stub inventory, quality profile |
| P2 — Competitive Intelligence | Research 10+ proprietary platforms, 7+ open-source projects | Feature matrix, pricing models, differentiators |
| P3 — Gap Analysis | Cross-reference JoBot capabilities vs market baseline | Prioritized feature/improvement list |
| P4 — Phased Roadmap | Sequence improvements by dependency, risk, and leverage | 8 implementation phases with entry/exit criteria |
| P5 — Risk & Questions | Identify blockers, ambiguities, decision points | Risk register + clarification questions for owner |

### Guiding Principles (from AGENTS.md)

> [!IMPORTANT]
> These are non-negotiable constraints that shape every decision in this plan:
> 1. **Working system > beautiful description** — every phase must leave a demonstrably better system
> 2. **Observable > clever** — transparent state models, file-based project OS, visible evidence
> 3. **Verification-first** — nothing is done until checks prove it
> 4. **Local-first, privacy-preserving** — no phone-home, BYOK for LLMs, encrypted profile vault
> 5. **Human-in-the-loop governance** — checkpoint before consequential side effects
> 6. **Idempotent submissions** — safe retries, saga compensations, dedup
> 7. **Truth-first** — zero hallucinated credentials, grounded QA, PII masking

---

## 2. Current State Audit

### 2.1 Architecture Overview

JoBot is a **dual-stack** application: Python 3.11+ backend (primary) + Tauri 2 / React desktop GUI (early stage).

```
src/jobot/ (116 files, ~509 KB)
├── adapters/       # 8 ATS site adapters (Naukri, LinkedIn, Workday, Greenhouse, Lever, Indeed, MockATS, GenericPortal)
├── ai/             # Skill extraction, QA engine
├── analytics/      # Skill-gap analysis, salary benchmarking
├── asp/            # 12-phase Application Submission Pipeline + saga orchestrator
├── cli/            # 1749-line Typer CLI with 25+ commands
├── config/         # Three-tier config manager (env → keyring → YAML)
├── digest/         # Weekly email digest generator
├── discovery/      # Job discovery engine with match scoring
├── documents/      # Resume tailoring (drafter→reviewer), cover letters, PDF export (LaTeX + fallback), ATS scoring
├── evals/          # 6-category evaluation harness
├── failure/        # Error resolution and retry logic
├── gui/            # Tauri sidecar JSON-RPC bridge
├── interview/      # Mock interview sessions with STAR coaching
├── llm/            # 12-provider ModelRouter v2 with cost-aware routing
├── memory/         # Vector memory (cosine similarity RAG)
├── models/         # Pydantic v2 domain models (15+ models)
├── notify/         # Email sender (SMTP)
├── obs/            # Tracing (OpenTelemetry-compatible), alerts, manual test logger
├── outreach/       # Cold DM generation with grounding gates
├── plugins/        # Plugin installer + manifest auditor
├── policy/         # Governance: daily/weekly caps, risk enforcement
├── scheduler/      # 4-mode loop executor (scan/apply/digest/full-loop)
├── scrapers/       # JobSpy integration, ATS API scrapers, career page scanner, dedup
├── security/       # PII masker (regex-based tokenization)
├── stealth/        # Browser session, circuit breaker, HTTP client with TLS fingerprint
├── storage/        # SQLite WAL database + Fernet encrypted vault
├── tracker/        # Application tracking analytics + HTML dashboard renderer
└── workflows/      # ApplicationWorkflow with approval signals

gui/ (Tauri 2 + React 18)
├── src/            # App.jsx, main.jsx, styles.css, views/, lib/
├── src-tauri/      # Rust sidecar config
└── tests/          # GUI tests

tests/ (74 files, ~252 KB)
├── 60+ pytest files covering core modules
├── integration/    # End-to-end mock ATS tests
├── mock_ats/       # Flask-based mock ATS server
├── mock_linkedin/  # LinkedIn mock fixtures
├── npm/            # Vitest tests
└── evals/          # Evaluation test fixtures
```

### 2.2 What Works Today (Strengths)

| Capability | Status | Evidence |
|---|---|---|
| 12-phase ASP pipeline | ✅ Functional | `pipeline.py` ~360 lines, phase dispatching, DoDResult returns |
| 8 site adapters | ✅ Scaffolded with real verification | `VerificationResult` returns with confirmation IDs |
| 12-provider LLM router | ✅ Cost-aware with fallback chain | `router.py` 277 lines, daily budget, spend persistence |
| Resume tailoring (drafter→reviewer) | ✅ Functional | `tailor.py` 18 KB, A-F rubric, truthfulness gates |
| Cover letter generation | ✅ 5 tone presets | `cover.py` 4.7 KB |
| PDF export (LaTeX + fallback) | ✅ Dual engine | `pdf_exporter.py` + `compiler.py` + `engines.py` |
| ATS parseability scoring | ✅ Functional | `ats.py` with pass/fail checks |
| Job scraping (6 boards via JobSpy) | ✅ Functional | `jobspy.py` + circuit breaker + dedup |
| Encrypted profile vault | ✅ Fernet + OS keyring | `vault.py` with master key fallback |
| Config management | ✅ Three-tier | env → keyring → YAML with secret masking |
| CI/CD | ✅ 12-job matrix + CodeQL + SBOM | `ci.yml` 123 lines, supply chain attestation |
| Mock interview sessions | ✅ STAR coaching | `coach.py` + `sessions.py` + question banks |
| Plugin system | ✅ Install + audit + manifest | `installer.py` + `auditor.py` |
| Skill-gap analysis | ✅ Functional | `analytics/skill_gap.py` |
| Salary benchmarking | ✅ Reference data | `analytics/salary.py` with YAML data |
| Outreach / cold DM generation | ✅ Grounding gates | `outreach/dm.py` with daily caps |
| Scheduler (4 modes) | ✅ Functional | `scheduler/loop.py` |
| Saga orchestrator | ✅ Checkpointable | `asp/saga.py` + `asp/orchestrator.py` |
| PII masker | ✅ Functional | `security/pii_masker.py` |
| Vector memory | ✅ Local cosine similarity | `memory/vector.py` |
| Tauri 2 GUI shell | 🔶 Early stage | App.jsx + sidecar bridge exist but minimal views |
| Docker packaging | ✅ Multi-stage | Dockerfile + docker-compose.yml |
| 85+ pytest tests passing | ✅ Verified | ruff + mypy strict + pytest + vitest all green |

### 2.3 Critical Gaps & Technical Debt

| Category | Issue | Severity | Files |
|---|---|---|---|
| **Stubs** | LLM streaming: `NotImplementedError` for all 6+ providers | HIGH | `llm/providers.py` |
| **Stubs** | ATS direct scrapers: `NotImplementedError` | MEDIUM | `scrapers/ats.py` |
| **Stubs** | LinkedIn deeper profile actions: `NotImplementedError` | HIGH | `adapters/linkedin.py` |
| **Error handling** | Silent `except Exception: pass` blocks | MEDIUM | `storage/vault.py`, adapter fallbacks |
| **CLI monolith** | Single 1749-line `main.py` file | HIGH | `cli/main.py` |
| **GUI** | Minimal — only sidecar bridge and shell App.jsx | HIGH | `gui/` |
| **Test gaps** | Scraper tests opt-in only; GUI untested; stealth integration sparse | MEDIUM | Multiple |
| **Documentation** | README is 26 lines; no API docs, no architecture diagram | HIGH | `README.md` |
| **Observability** | Tracing writes files but no structured export or dashboard integration | MEDIUM | `obs/tracing.py` |
| **Configuration** | Hardcoded defaults (e.g., `location_city="Bangalore"`, `skills=["Python", ...]`) in profile init | LOW | `cli/main.py` L135-145 |
| **Deprecated API** | `datetime.utcnow()` usage (deprecated in Python 3.12+) | LOW | `models/domain.py` L202 |
| **Format CI** | Ruff format only checks `src/`, not `tests/` | LOW | `ci.yml` L42 |
| **Security** | `.env` file exists in repo root (not in `.gitignore`?) | HIGH | `.env` at root |
| **Missing** | No CHANGELOG, no CONTRIBUTING guide, no CODE_OF_CONDUCT | MEDIUM | — |
| **Missing** | No structured logging (only Python stdlib `logging`) | MEDIUM | Multiple |

---

## 3. Competitive Landscape & Feature Intelligence

### 3.1 Proprietary Platforms

| Platform | Pricing | Key Features | Differentiator | Weakness |
|---|---|---|---|---|
| **Simplify.jobs** | Free / $39.99/mo | Autofill extension, multi-ATS, tracking | Best autofill accuracy across Workday/Greenhouse/etc. | No auto-apply while away |
| **Teal HQ** | Free / $29/mo | Resume builder, Kanban tracker, ATS keyword checker | Best organizational UX | Tracking only, no automation |
| **JobRight.ai** | Free / $39.99/mo | AI copilot, resume tailoring, Chrome autofill | Conversational AI coach ("Orion") | Pricey, sometimes generic output |
| **Careerflow** | Free / ~$22/mo | LinkedIn profile scorer, interview prep | Best LinkedIn profile review | Optimization only, no apply |
| **Sonara.ai** | $2.95 trial / $23.95/mo | Continuous scan + auto-submit | "Set and forget" passive search | Generic applications, low conversion |
| **LazyApply** | $99–$999/yr | Mass 1-click apply | Volume | Poor reviews, untailored, bans risk |
| **Massive.app** | ~$117/quarter | Fully hands-off apply service | Zero effort | Volume-over-quality, auto-rejections |
| **Huntr** | Free / $40/mo | Kanban tracker, Job Clipper | Visual pipeline management | No apply automation |
| **LoopCV** | Free / €10–30/mo | Auto-apply, email outreach, A/B resume testing | Resume A/B testing with metrics | Spray-and-pray quality issues |
| **Autoapply.jobs** | Subscription | Auto-scan + auto-submit | Hands-off | Generic applications |

### 3.2 Open-Source Projects

| Project | Stars | License | Key Features | What to Absorb |
|---|---|---|---|---|
| **career-ops** (santifer) | 63,659 | MIT | Plugin registry, A-F rubric, ~120 capability scripts, 17 CI workflows | Plugin architecture, capability catalog, CI patterns |
| **ai-job-search** (MadsLorentzen) | 31,411 | MIT | Drafter→reviewer loop, LaTeX CV pipeline, slash commands | Two-agent loop pattern (already absorbed), `/setup` profile ingestion |
| **AIHawk** (feder-cr) | 30,159 | AGPL-3.0 | LinkedIn Easy Apply automation, dynamic form Q&A | Question-answering module, form handling patterns |
| **JobSpy** (speedyapply) | 4,072 | MIT | Multi-board job scraping library | Already vendored as pip dep ✅ |
| **Reactive-Resume** | 35k+ | MIT | Free resume builder, BYOK OpenAI, self-hosted | Resume template system, ATS optimization patterns |
| **OpenResume** | 6k+ | MIT | ATS-optimized resume parser + builder | PDF resume parsing algorithm |
| **Auto_job_applier_linkedIn** (GodsScion) | 2,688 | MIT | LinkedIn-specific resilience patterns | Retry patterns, selector healing |

### 3.3 Market Positioning Map

```
                    Tailored Quality
                         ▲
                         │
        Simplify ●       │       ● JoBot (target)
         Teal ●          │
      JobRight ●         │       ● career-ops
   Careerflow ●          │
                         │
  ─────────────────────────────────────────► Automation Level
                         │
         Huntr ●         │       ● AIHawk
                         │       ● LoopCV
                         │
                         │  ● Sonara  ● LazyApply
                         │  ● Massive ● Autoapply
                         │
                    Generic Volume
```

**JoBot's target quadrant:** HIGH tailored quality + HIGH automation — the least populated and most defensible position.

---

## 4. Gap Analysis: JoBot vs Market

### 4.1 Feature Parity Matrix

| Feature | JoBot | Simplify | Teal | AIHawk | career-ops | Priority |
|---|---|---|---|---|---|---|
| Multi-board job scraping | ✅ | ❌ | ❌ | ❌ | ✅ | — |
| Resume tailoring (AI) | ✅ | ❌ | ✅ | ✅ | ✅ | — |
| Cover letter generation | ✅ | ❌ | ✅ | ✅ | ✅ | — |
| Auto-fill forms | ✅ | ✅ | ❌ | ✅ | ❌ | — |
| Auto-submit applications | ✅ | ❌ | ❌ | ✅ | ❌ | — |
| ATS score checking | ✅ | ❌ | ✅ | ❌ | ❌ | — |
| Kanban/visual tracker | 🔶 CLI only | ❌ | ✅ | ❌ | ✅ | **P4** |
| **LLM streaming responses** | ❌ STUB | — | — | — | — | **P1** |
| **Real LinkedIn Easy Apply** | 🔶 Stub | ❌ | ❌ | ✅ | ❌ | **P2** |
| **Resume PDF parsing (ingest)** | ❌ | ✅ | ✅ | ✅ | ❌ | **P3** |
| **Browser extension** | ❌ | ✅ | ✅ | ❌ | ❌ | **P7** |
| **LinkedIn profile scoring** | ❌ | ❌ | ❌ | ❌ | ❌ | **P7** |
| **Resume A/B testing** | ❌ | ❌ | ❌ | ❌ | ❌ | **P7** |
| **Real-time notifications** | ❌ | — | — | — | — | **P5** |
| **Multi-profile support** | 🔶 hardcoded "default" | ✅ | ✅ | ❌ | ❌ | **P2** |
| **Recruiter outreach** | ✅ | ❌ | ❌ | ❌ | ✅ | — |
| **Interview prep** | ✅ | ❌ | ❌ | ❌ | ✅ | — |
| **Encrypted local vault** | ✅ | ❌ | ❌ | ❌ | ❌ | — (unique) |
| **Plugin ecosystem** | ✅ | ❌ | ❌ | ❌ | ✅ | — |
| **CI/CD + SBOM** | ✅ | — | — | — | ✅ | — |
| **GUI desktop app** | 🔶 Shell | ❌ | Web | ❌ | ❌ | **P4** |
| **Docker packaging** | ✅ | — | ✅ | ❌ | ✅ | — |
| **API / headless mode** | 🔶 CLI only | — | — | ❌ | ✅ | **P6** |
| **Structured logging / OTEL** | 🔶 File only | — | — | ❌ | ❌ | **P5** |

### 4.2 Unique Competitive Advantages (JoBot Already Has)

1. **12-provider LLM router with cost-aware fallback** — no competitor has this breadth
2. **Encrypted local vault with OS keyring** — strongest privacy story in the market
3. **Saga orchestrator with compensating actions** — enterprise-grade reliability primitives
4. **PII masker before LLM transmission** — zero data leakage to cloud LLMs
5. **6-category evaluation harness** — continuous quality measurement (no competitor does this)
6. **Policy engine with daily/weekly caps** — prevents reckless mass-apply
7. **Circuit breaker per adapter** — fault isolation across boards

### 4.3 Features to Integrate from Competitors

| Feature | Source Inspiration | Implementation Effort | Impact |
|---|---|---|---|
| Resume PDF parsing/ingestion | OpenResume, Simplify | Medium | HIGH — onboarding friction reduction |
| LinkedIn Easy Apply completion | AIHawk, GodsScion | High | CRITICAL — #1 requested feature |
| Kanban visual tracker (GUI) | Teal, Huntr | Medium | HIGH — user retention |
| Resume A/B testing with metrics | LoopCV | Medium | MEDIUM — data-driven optimization |
| LinkedIn profile scorer | Careerflow | Medium | MEDIUM — unique value-add |
| Browser extension (Chrome/Firefox) | Simplify, Teal | High | HIGH — mass market reach |
| Conversational AI coach | JobRight ("Orion") | Medium | MEDIUM — differentiation |
| Real-time application status webhooks | None (novel) | Medium | HIGH — integration surface |

---

## 5. Phase 1: Foundation Hardening

**Timeline:** Weeks 1–3  
**Theme:** "Make what exists bulletproof before adding new features"

### 5.1 LLM Streaming Implementation

**Problem:** All 6+ providers raise `NotImplementedError` for streaming.  
**Impact:** Blocks real-time UI feedback, long-form generation UX, and cost-efficient token processing.

**Steps:**
1. Implement `stream()` for `GeminiProvider` using `google-genai` async streaming
2. Implement `stream()` for `OpenAIProvider` using `httpx` SSE
3. Implement `stream()` for `AnthropicProvider` using Messages API streaming
4. Implement `stream()` for `OpenAICompatProvider` (covers Groq, Together, OpenRouter, Ollama, vLLM)
5. Implement `stream()` for `MistralProvider` and `CohereProvider`
6. Add streaming fallback in `ModelRouter.generate_text_stream()` (new method)
7. Wire streaming into CLI for `jobot qa`, `jobot coverletter`, and `jobot interview answer`
8. Add pytest tests with mock SSE responses for each provider

**Exit Criterion:** `jobot qa "Tell me about yourself" --stream` renders tokens incrementally in terminal.

### 5.2 CLI Refactor

**Problem:** `cli/main.py` is a 1749-line monolith — hard to maintain, review, and test.

**Steps:**
1. Split into subcommand modules: `cli/apply.py`, `cli/scrape.py`, `cli/resume.py`, `cli/interview.py`, `cli/tracker.py`, `cli/config.py`, `cli/admin.py`
2. Register each as a Typer sub-app
3. Extract shared helpers (`_resolve_job`, `get_adapter`) to `cli/helpers.py`
4. Preserve all existing command signatures (frozen contract)
5. Add `jobot --version` command
6. Update CI to lint/format `cli/` submodules

**Exit Criterion:** All 25+ CLI commands work identically; `main.py` < 100 lines.

### 5.3 Error Handling & Logging Upgrade

**Steps:**
1. Replace all `except Exception: pass` blocks with explicit logging + optional metric emission
2. Add `structlog` dependency for structured JSON logging
3. Create `jobot.logging` module with configurable output (JSON for production, pretty for dev)
4. Add request ID / correlation ID propagation across async calls
5. Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` globally

**Exit Criterion:** `ruff check .` passes; `grep -r "except.*pass" src/` returns zero results.

### 5.4 Security Hardening

**Steps:**
1. Verify `.env` is in `.gitignore` (if not, add immediately + rotate any leaked keys)
2. Audit all `os.environ` reads for secret leakage paths
3. Add `bandit` (Python security linter) to CI pipeline
4. Add `pip-audit` for known vulnerability scanning in CI
5. Add CSP headers to any HTTP server endpoints
6. Review Fernet key rotation story (document in `SETUP.md`)

**Exit Criterion:** `bandit -r src/` and `pip-audit` pass clean in CI.

### 5.5 Test Coverage Expansion

**Steps:**
1. Add `pytest-cov` enforcement: fail CI if coverage drops below 70%
2. Write tests for untested modules: `digest/`, `notify/`, `outreach/`, `scheduler/loop.py`
3. Add negative/error-path tests for every adapter
4. Add integration test for full apply saga (mock ATS end-to-end)
5. Add property-based tests (via `hypothesis`) for PII masker patterns

**Exit Criterion:** `pytest --cov=jobot --cov-fail-under=70` passes in CI.

---

## 6. Phase 2: Core Pipeline Completion

**Timeline:** Weeks 4–7  
**Theme:** "Complete the flagship user journey: scrape → tailor → apply → verify"

### 6.1 LinkedIn Easy Apply Implementation

**Problem:** The #1 most requested feature in job automation. Current LinkedIn adapter has stubs.

**Steps:**
1. Implement `LinkedInEasyApplyFlow` on Patchright (stealth Playwright fork)
2. Handle: login session reuse, search → filter → Easy Apply button → multi-page form
3. Implement form-field detection (text, dropdown, radio, checkbox, file upload)
4. Wire `QAEngine` for dynamic question answering during form fill
5. Add screenshot evidence capture at each form page
6. Implement human-in-the-loop preview gate before final submit click
7. Add compensating action: navigate back / cancel if submission fails mid-form
8. Add anti-detection: realistic delays, mouse movement, scroll behavior
9. Test with real LinkedIn account on staging (manual verification required)

**Exit Criterion:** `jobot apply --url <linkedin-easy-apply-url>` completes full 12-phase pipeline with screenshot evidence.

### 6.2 Multi-Profile Support

**Problem:** Hardcoded `profile_id="default"` throughout. Users need multiple profiles for different job targets.

**Steps:**
1. Add `--profile` flag to all CLI commands that load profiles
2. Update `CredentialVault.save/load_encrypted_profile()` to support named profiles
3. Add `jobot profile list`, `jobot profile switch <name>`, `jobot profile export/import`
4. Update saga orchestrator to carry profile_id through checkpoints
5. Update database schema to associate applications with profile_id

**Exit Criterion:** `jobot apply --profile backend_senior --url <url>` uses the correct profile.

### 6.3 Resume PDF Parsing / Ingestion

**Problem:** Users must manually enter all profile data. Competitors parse existing PDFs.

**Steps:**
1. Implement `ResumeParser` using `pdfminer.six` (already a dependency) + regex extraction
2. Parse: name, email, phone, education, work experience, skills
3. Add LLM-assisted extraction for ambiguous fields (via ModelRouter)
4. Add `jobot profile import-resume <path.pdf>` command
5. Add validation: show parsed result, ask user to confirm before saving
6. Wire into GUI onboarding flow

**Exit Criterion:** `jobot profile import-resume resume.pdf` creates an encrypted profile with ≥80% field accuracy on standard resumes.

### 6.4 Direct API Apply (Greenhouse, Lever, Ashby)

**Problem:** These ATS platforms have public APIs — browser automation is unnecessary overhead.

**Steps:**
1. Implement `GreenhouseAdapter.submit_application()` via Greenhouse Harvest API
2. Implement `LeverAdapter.submit_application()` via Lever Postings API
3. Add `AshbyAdapter` with full discover + parse + submit via Ashby API
4. Add `SmartRecruitersAdapter` for SmartRecruiters public API
5. All submissions go through saga orchestrator with idempotency keys

**Exit Criterion:** `jobot apply --url https://boards.greenhouse.io/company/jobs/123` submits via API without browser.

---

## 7. Phase 3: Intelligence & Matching Layer

**Timeline:** Weeks 8–11  
**Theme:** "Make JoBot smart enough to find and rank the right jobs"

### 7.1 Enhanced Job Matching Engine

**Steps:**
1. Implement embedding-based job-profile matching (replace keyword overlap)
2. Add configurable match dimensions: skills, experience level, location, compensation range, industry
3. Add match explanation: "Matched because: 85% skill overlap, location match, 3+ YOE required vs your 5"
4. Store match scores with applications for analytics
5. Add `jobot match <job-url>` standalone command for quick compatibility check

### 7.2 Conversational AI Assistant

**Steps:**
1. Implement `jobot ask <question>` — natural language interface to all JoBot data
2. Route queries: "How many applications this week?" → tracker, "What skills am I missing?" → analytics
3. Support follow-ups with session context
4. Wire through ModelRouter with `task="assistant"` for model routing

### 7.3 Resume A/B Testing Framework

**Steps:**
1. Track which resume variant was sent to each application
2. Track callback/response rate per variant
3. Implement `jobot resume variants` to manage A/B groups
4. Implement `jobot resume report` to show conversion metrics per variant
5. Auto-promote best-performing variant after N applications

### 7.4 LinkedIn Profile Analyzer

**Steps:**
1. Implement `jobot linkedin score` — parse LinkedIn profile page and score SEO/recruiter visibility
2. Check: headline quality, summary length, skill endorsements, connection count, activity
3. Generate actionable recommendations
4. Compare profile against target role requirements

---

## 8. Phase 4: User-Facing Surface & GUI

**Timeline:** Weeks 12–16  
**Theme:** "Make JoBot visually compelling and accessible to non-CLI users"

### 8.1 Tauri 2 Desktop GUI Completion

The GUI shell exists (`gui/src/App.jsx`) but has minimal functionality.

**Steps:**
1. **Dashboard View** — active campaigns, recent applications, success rate, daily quota remaining
2. **Job Board View** — scraped jobs in a sortable/filterable table with match scores
3. **Application Detail View** — saga state, form values, evidence screenshots, timeline
4. **Profile Editor** — visual profile editing with encrypted save
5. **Resume Preview** — live preview of tailored resume with ATS score overlay
6. **Settings Panel** — LLM provider config, adapter toggles, policy caps, theme
7. **Interview Coach View** — interactive mock interview with real-time STAR feedback
8. **Notifications** — toast notifications for completed applications, errors, cap warnings

**Tech Stack:** React 18 + Tailwind CSS + Tauri 2 IPC via sidecar bridge.

**Exit Criterion:** `jobot sidecar` + `npm run tauri:dev` renders a functional dashboard with live data from the Python backend.

### 8.2 Terminal UI (TUI) Enhancement

For power users who prefer CLI:

**Steps:**
1. Add `jobot tui` command launching a `textual`-based terminal dashboard
2. Panels: live scrape progress, application queue, saga status, LLM cost tracker
3. Keyboard shortcuts for common actions
4. Real-time streaming output from ongoing operations

### 8.3 HTML Report Generator

**Steps:**
1. Enhance `TrackerRenderer.render_html_file()` with interactive charts (Chart.js)
2. Add funnel visualization: Scraped → Matched → Applied → Responded → Interview → Offer
3. Add weekly trend charts
4. Add export-as-PDF option
5. `jobot tracker dashboard-html --open` auto-opens in browser

---

## 9. Phase 5: Observability, Governance & Trust

**Timeline:** Weeks 17–20  
**Theme:** "Make every action visible, auditable, and governable"

### 5.1 Structured Telemetry Pipeline

**Steps:**
1. Migrate from file-based tracing to OpenTelemetry SDK
2. Add spans for: LLM calls, scraper requests, form fills, saga phases, adapter calls
3. Add metrics: applications/day, cost/day, success rate, latency percentiles
4. Add optional Jaeger/Zipkin export for local visualization
5. Add `jobot traces export --format otlp` for external consumption

### 5.2 Trust Level Automation

**Steps:**
1. Implement trust score calculation based on: success rate, error rate, human override frequency
2. Auto-promote adapters from SUPERVISED → GUIDED after 10 successful submissions
3. Auto-demote on 3 consecutive failures
4. Add `jobot trust show` and `jobot trust set <adapter> <level>` commands
5. Log trust transitions as audit events

### 5.3 Budget & Cost Dashboard

**Steps:**
1. Implement `jobot cost show` — daily/weekly/monthly LLM spend by provider and task type
2. Add cost alerts when approaching budget limits
3. Add cost-per-application metric
4. Wire cost data into GUI dashboard

### 5.4 Audit Log

**Steps:**
1. Implement append-only audit log for all consequential actions
2. Fields: timestamp, action, actor (user/system), target, outcome, evidence_path
3. Add `jobot audit show --since 7d` command
4. Add tamper detection (hash chain)

---

## 10. Phase 6: Production Infrastructure

**Timeline:** Weeks 21–24  
**Theme:** "Production-grade packaging, deployment, and operations"

### 6.1 Docker Hardening

**Steps:**
1. Add health check endpoint to Docker image
2. Add `docker-compose.yml` profiles: `dev`, `production`, `ci`
3. Add Patchright browser installation to Docker image (headless mode)
4. Add volume mounts for persistent state (`~/.jobot/`)
5. Add resource limits and security contexts

### 6.2 PyPI Publication

**Steps:**
1. Set up `trusted publisher` on PyPI via GitHub Actions
2. Add `publish.yml` workflow triggered on GitHub Release tags
3. Add `CHANGELOG.md` with Keep a Changelog format
4. Add `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`
5. Test: `pip install jobot` → `jobot doctor` passes

### 6.3 API Server Mode

**Steps:**
1. Implement `jobot serve` — FastAPI server exposing JoBot capabilities as REST API
2. Endpoints: `/scrape`, `/apply`, `/profile`, `/tracker`, `/config`, `/health`
3. API key authentication
4. OpenAPI schema auto-generation
5. This enables: webhooks, integrations, headless operation, remote workers

### 6.4 Homebrew / OS Package Managers

**Steps:**
1. Create Homebrew formula: `brew install jobot`
2. Create Scoop manifest for Windows
3. Create Snap / Flatpak for Linux desktop users

---

## 11. Phase 7: Advanced Features & Differentiation

**Timeline:** Weeks 25–32  
**Theme:** "Build features no competitor has"

### 7.1 Browser Extension (Chrome/Firefox)

**Steps:**
1. Build Manifest V3 Chrome extension
2. "Apply with JoBot" button injected on job posting pages
3. Extension communicates with local `jobot serve` API
4. Form detection + autofill via content scripts
5. One-click apply flow with preview modal

### 7.2 Proactive Job Discovery Agent

**Steps:**
1. Implement always-on background scanner (configurable schedule)
2. Alert user when high-match jobs appear (desktop notification)
3. Auto-save and pre-tailor materials for top matches
4. Weekly "opportunity digest" email with curated top matches

### 7.3 Application Outcome Learning Loop

**Steps:**
1. Track: application → response/silence → interview → offer/rejection
2. Use outcome data to refine match scoring model
3. Identify which resume variants, cover letter tones, and application timing correlate with success
4. Surface insights: "Applications sent Monday 9AM have 2.3x higher response rate"

### 7.4 Multi-Language Resume Support

**Steps:**
1. Add resume templates for non-English markets (German Lebenslauf, Japanese 履歴書, etc.)
2. Add LLM-based translation with industry-specific terminology
3. Support region-specific formatting (photo/no-photo, date formats, etc.)

### 7.5 Networking Graph & Referral Tracking

**Steps:**
1. Track contacts, companies, and referral relationships
2. Suggest warm introductions based on network proximity
3. Track referral-sourced applications separately for conversion comparison

---

## 12. Phase 8: Release Engineering & Launch

**Timeline:** Weeks 33–36  
**Theme:** "Ship v1.0 to the public"

### 8.1 v1.0 Release Criteria

| Criterion | Threshold |
|---|---|
| All Phase 1-4 features implemented | ✅ |
| Phase 5 observability basics operational | ✅ |
| pytest coverage ≥ 75% | ✅ |
| ruff + mypy strict clean | ✅ |
| `jobot doctor` passes on macOS, Linux, Windows (WSL2) | ✅ |
| 3 real successful LinkedIn Easy Apply submissions verified | ✅ |
| GUI dashboard functional with live data | ✅ |
| README comprehensive (badges, screenshots, quickstart) | ✅ |
| CHANGELOG, CONTRIBUTING, LICENSE present | ✅ |
| Docker image published to GHCR | ✅ |
| PyPI package published | ✅ |

### 8.2 Launch Checklist

1. GitHub Release with semantic version tag
2. README with: badges, demo GIF, quickstart, architecture diagram
3. Blog post / README section explaining philosophy (privacy-first, truth-first, human-governed)
4. Submit to: Hacker News, r/Python, r/jobs, Product Hunt
5. Create GitHub Discussions for community Q&A
6. Set up issue templates (bug report, feature request, adapter request)
7. Tag initial GitHub issues for "good first issue" to attract contributors

### 8.3 Post-Launch Operations

1. Weekly GitHub issue triage
2. Monthly release train (semver)
3. Dependabot + security advisory monitoring (already configured)
4. Adapter health monitoring (scraper breakage detection)
5. Community plugin curation

---

## 13. Clarification Questions

> [!IMPORTANT]
> The following questions will materially impact implementation decisions. Please review and answer before Phase 1 begins.

### Architecture & Scope

1. **GUI priority:** Is the Tauri 2 desktop GUI a v1.0 requirement, or can v1.0 ship as CLI-only with GUI as v1.1? This significantly impacts timeline.

2. **Browser extension:** Should we plan for a Chrome extension in the initial release, or defer to v2.0? This is a separate codebase and maintenance burden.

3. **API server mode:** Is `jobot serve` (REST API) in scope for v1.0? This enables headless deployment and webhook integrations.

### Target Market & Priorities

4. **Geographic focus:** Is India the primary market (Naukri, LinkedIn India)? Or should we equally prioritize US/EU markets (Indeed US, Glassdoor, ZipRecruiter)? This determines adapter priority.

5. **Job level focus:** Entry-level mass-apply or senior/specialized targeted applications? The matching engine design differs significantly.

6. **Platform priority ordering:** Rank these by importance for v1.0: LinkedIn Easy Apply, Naukri, Greenhouse API, Lever API, Indeed, Workday, Other.

### Technical Decisions

7. **LLM provider default:** The current default is Gemini (free tier). Should we optimize for Gemini users or make it truly provider-agnostic from day one?

8. **Patchright dependency:** Patchright is a fork of Playwright with stealth patches. It's excellent but niche. Should we also support vanilla Playwright as a fallback for users who don't need stealth?

9. **Database scaling:** SQLite WAL is the current default (as per AGENTS.md). At what user/data scale should we offer a Postgres migration path?

10. **Resume format:** Should we invest in LaTeX-based resume generation (requires TeX installation) or prioritize HTML-to-PDF (zero external dependencies)?

### Operations & Community

11. **Open-source governance:** AGPL-3.0 is strong copyleft. Are you open to dual-licensing (AGPL for open-source, commercial for enterprise) in the future?

12. **Contributor readiness:** Do you want to optimize for solo development speed or community contribution readiness (docs, issue templates, mentoring)?

13. **Timeline:** Is there a hard deadline (e.g., job search timing) or is this an ongoing project?

---

## 14. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | LinkedIn detects Patchright and bans accounts | HIGH | CRITICAL | Session reuse, realistic delays, daily caps, human fallback, circuit breaker |
| R2 | JobSpy selectors break on board redesigns | MEDIUM | HIGH | Pin version, health-check cron, alert on circuit breaker opening, fallback to direct API |
| R3 | LLM API rate limits during batch operations | MEDIUM | MEDIUM | Fallback chain, circuit breaker per provider, daily cost cap, local Ollama fallback |
| R4 | AGPL license deters enterprise adoption | LOW | MEDIUM | Dual-license option, clear documentation of what AGPL requires |
| R5 | Patchright fork falls behind upstream Playwright | MEDIUM | MEDIUM | Monitor upstream, contribute patches back, maintain vanilla Playwright fallback |
| R6 | GUI development delays block v1.0 | MEDIUM | MEDIUM | CLI-first release strategy; GUI is v1.1 if needed |
| R7 | Saga left in half-applied state | LOW | HIGH | Compensating actions, checkpoint per phase, quarantine queue |
| R8 | PII leakage to LLM providers | LOW | CRITICAL | PII masker before all LLM calls (already implemented), audit logging |
| R9 | `.env` file with secrets in repo | HIGH | HIGH | Immediate: verify .gitignore, rotate any leaked keys |
| R10 | CLI monolith becomes unmaintainable | HIGH | MEDIUM | Phase 1 refactor into subcommand modules |
| R11 | Adapter maintenance burden grows with each new board | MEDIUM | MEDIUM | Plugin architecture for community adapters, adapter health monitoring |
| R12 | Test suite becomes slow as coverage increases | LOW | LOW | Parallel test execution, mock-heavy unit tests, opt-in integration tests |

---

## 15. Appendices

### Appendix A: Feature Integration Priority Matrix

Features ranked by: **Impact × Feasibility ÷ Effort**

| Rank | Feature | Impact | Feasibility | Effort | Score |
|---:|---|---|---|---|---|
| 1 | LLM streaming (de-stub) | HIGH | HIGH | LOW | ★★★★★ |
| 2 | CLI refactor (split monolith) | HIGH | HIGH | LOW | ★★★★★ |
| 3 | Error handling cleanup | HIGH | HIGH | LOW | ★★★★★ |
| 4 | LinkedIn Easy Apply | CRITICAL | MEDIUM | HIGH | ★★★★☆ |
| 5 | Resume PDF parsing | HIGH | HIGH | MEDIUM | ★★★★☆ |
| 6 | Multi-profile support | HIGH | HIGH | MEDIUM | ★★★★☆ |
| 7 | Direct API apply (Greenhouse/Lever) | HIGH | HIGH | MEDIUM | ★★★★☆ |
| 8 | GUI dashboard (Tauri 2) | HIGH | MEDIUM | HIGH | ★★★☆☆ |
| 9 | Structured logging (OTEL) | MEDIUM | HIGH | MEDIUM | ★★★☆☆ |
| 10 | Trust level automation | MEDIUM | HIGH | MEDIUM | ★★★☆☆ |
| 11 | Enhanced job matching (embeddings) | HIGH | MEDIUM | MEDIUM | ★★★☆☆ |
| 12 | Resume A/B testing | MEDIUM | MEDIUM | MEDIUM | ★★☆☆☆ |
| 13 | Browser extension | HIGH | MEDIUM | HIGH | ★★☆☆☆ |
| 14 | API server mode | MEDIUM | HIGH | MEDIUM | ★★★☆☆ |
| 15 | LinkedIn profile scorer | MEDIUM | MEDIUM | MEDIUM | ★★☆☆☆ |

### Appendix B: Dependency Additions Required

| Package | Phase | Purpose | License |
|---|---|---|---|
| `structlog` | P1 | Structured JSON logging | MIT |
| `bandit` (dev) | P1 | Security linting | Apache-2.0 |
| `pip-audit` (dev) | P1 | Vulnerability scanning | Apache-2.0 |
| `hypothesis` (dev) | P1 | Property-based testing | MPL-2.0 |
| `textual` | P4 | Terminal UI framework | MIT |
| `fastapi` + `uvicorn` | P6 | REST API server | MIT + BSD |
| `opentelemetry-sdk` | P5 | Structured tracing | Apache-2.0 |
| `opentelemetry-exporter-otlp` | P5 | OTLP export | Apache-2.0 |

### Appendix C: File Size Hot Spots (Refactor Candidates)

| File | Lines | Bytes | Action |
|---|---|---|---|
| `cli/main.py` | 1,749 | 69.5 KB | **Split into 7 submodules** (Phase 1) |
| `llm/providers.py` | ~500 | 19.1 KB | De-stub streaming (Phase 1) |
| `documents/tailor.py` | ~500 | 18.8 KB | Stable — no action needed |
| `adapters/workday.py` | ~400 | 16.1 KB | Stable — complex but necessary |
| `gui/sidecar.py` | ~350 | 13.1 KB | Extend during GUI phase (Phase 4) |

### Appendix D: CI/CD Enhancement Roadmap

| Current | Addition | Phase |
|---|---|---|
| ruff check + format | + bandit + pip-audit | P1 |
| mypy strict | (already present) | — |
| pytest | + pytest-cov --cov-fail-under=70 | P1 |
| vitest | + Playwright component tests (GUI) | P4 |
| CodeQL | (already present) | — |
| SBOM + attestation | (already present) | — |
| — | + release workflow (PyPI publish) | P6 |
| — | + adapter health check cron | P6 |

---

> [!NOTE]
> This plan is a living document. It will be updated as clarification questions are answered
> and as implementation reveals new constraints or opportunities.

**Next action:** Review clarification questions in §13, provide answers, then approve Phase 1 for execution.