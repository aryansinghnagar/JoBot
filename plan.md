# JoBot Merge Plan

**Version:** Draft 1.0 · 2026-08-13
**Target:** [aryansinghnagar/JoBot](https://github.com/aryansinghnagar/JoBot)
**License:** AGPL-3.0
**Companion document:** [SETUP.md](./SETUP.md) (full setup docs) · [JoBot_Merge_Plan.pdf](./JoBot_Merge_Plan.pdf) (127-page PDF version)

---

## Executive Summary

This is an architectural blueprint and operational playbook for merging the best functionality of **33 open-source job-search AI repositories** into `aryansinghnagar/JoBot` — a Python AGPL-3.0 project that has, as of August 2026, zero GitHub stars but the most sophisticated runtime primitives of any repo surveyed. The merge thesis is unusual: JoBot is **not an empty vessel being filled**. It is an architecturally ambitious chassis — async task graph, stealth browser, provider-neutral LLM router, encrypted storage, policy engine — onto which capability modules from higher-star repos must be **grafted, not copied**.

Three Tier-1 source repositories define the capability surface to absorb:

| Repo | Stars | Lang/License | What we lift |
|---|---:|---|---|
| [santifer/career-ops](https://github.com/santifer/career-ops) | 63,659 | JS/MIT | Plugin registry, A-F rubric scoring, ~120 capability scripts, 17 CI workflows |
| [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | 31,411 | TS/MIT | Drafter→reviewer loop, LaTeX CV pipeline, slash-command UX |
| [feder-cr/Jobs_Applier_AI_Agent_AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) | 30,159 | Py/AGPL-3.0 | Question-answering module, LinkedIn Easy Apply flow |

**Highest-leverage single decision:** vendor [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) (4,072★ MIT) as a pip dependency. One line in `pyproject.toml` gives JoBot 6 production board scrapers behind its existing adapter + circuit-breaker primitives.

**Multi-LLM provider support:** Gemini (default) + OpenAI + Anthropic + OpenAI-compatible (OpenRouter/Groq/Together/Ollama/vLLM) + Mistral + Cohere + AWS Bedrock + Google Vertex AI. Strategy-pattern `LLMProvider` abstraction. Cost-aware routing. Fallback chain.

**Roadmap:** 5 phases over 15+ weeks.

---

## Part I — Context & Audit

### Chapter 1 — Scope, Assumptions & Methodology

**Scope:** the JoBot core repository (CLI, engine, adapters, capability modules, configuration, deployment artifacts). Out of scope: hosted SaaS, mobile client, browser extension, Slack/Discord bot, paid third-party services beyond LLM API access.

**Assumptions:**

- **A1.** JoBot's existing runtime primitives (async task graph, ModelRouter, SQLite WAL control plane, Fernet encryption, OS keyring integration, Patchright stealth browser, circuit breaker, PII masker, vector memory) are real, tested, and remain the substrate for all merged capabilities.
- **A2.** Python 3.11+ is the target runtime. Async-first.
- **A3.** JoBot's AGPL-3.0 license is non-negotiable. AGPL/GPL/MIT/BSD/Apache code may be vendored; NOASSERTION/None code may be referenced for design but must be re-implemented.
- **A4.** Patchright (stealth Playwright fork) is the primary browser automation layer. Selenium-based modules will be re-implemented on Patchright.
- **A5.** The user supplies their own LLM API keys. No free-tier abuse, no shared keys.
- **A6.** Job boards will continue to evolve their anti-automation defenses. The architecture must make repair cheap.
- **A7.** The user is technically literate.
- **A8.** JoBot is a force multiplier, not a recruiter replacement. Human-in-the-loop checkpoint before any external side effect more consequential than a job "save".

**Methodology:** 33 repos inventoried via GitHub REST API on 2026-08-13. Star counts are API-verified. Full research artifact: [`repo_research.md`](./repo_research.md).

### Chapter 2 — JoBot Current State Audit

**What it has today:** Typer+rich CLI, async task-graph engine, Patchright stealth browser, SQLite WAL control plane + Fernet + OS Keyring, 4-provider ModelRouter, Greenhouse adapter, adapter registry, circuit breaker, captcha solver hook, dedup, policy engine (caps + enforcement), 12-phase Application State Protocol, tracing + QA engine + alerts, skill extraction + discovery, vector memory, PII masker, ~30 pytest files, Ruff+mypy strict CI, AGPL-3.0.

**Twelve capability gaps (priority order):**

1. **Production scrapers for major job boards** — lift from JobSpy + career-ops portal-health-locking pattern.
2. **LaTeX / PDF resume tailoring** — lift drafter→reviewer + LaTeX pipeline from MadsLorentzen.
3. **Cover-letter generation** — lift `generate-cover-letter.mjs` pattern from career-ops.
4. **Interview prep module** — lift `interview-prep/` from career-ops + `/interview` skill from ai-job-search.
5. **Application tracking dashboard / analytics** — lift dashboard patterns from career-ops + jobsync UX reference.
6. **Real ATS portal scanner** — lift `discover-ats.mjs`, `scan-ats-full.mjs`, `detect-reposts.mjs` from career-ops.
7. **Docker / container packaging** — lift Dockerfile + compose from career-ops or job-ops.
8. **Multi-board question-answering AI** — lift from AIHawk, re-implement behind ModelRouter.
9. **Outreach / cold-DM generation** — lift profile-driven outreach pipeline from replyre/job-hunter.
10. **Scheduler / daily-loop** — lift daily-digest scheduler from replyre/job-hunter + modes/ from career-ops.
11. **Salary benchmarking** — lift `salary_lookup.py` from ai-job-search + `salary-gap.mjs` from career-ops.
12. **Plugin install / audit flow** — lift `plugin-install.mjs`, `plugin-audit.mjs`, `plugins-registry/` from career-ops.

**Verdict:** JoBot is **architecturally the most ambitious** of the surveyed repos and **functionally the emptiest** in user-facing capabilities. Merge = graft capability modules onto the chassis, re-implementing them behind JoBot's existing abstractions.

### Chapter 3 — Source Repository Inventory

Full inventory: 33 repos, sorted by stars descending. See [Appendix A](#appendix-a-full-source-repository-star-inventory) below, or the full research file [`repo_research.md`](./repo_research.md).

**Tier 1 (10k+ stars):** career-ops (63k), ai-job-search (31k), AIHawk (30k)
**Tier 2 (1k–10k):** JobSpy (4k), job-ops (3.8k), Auto_job_applier_linkedIn (2.7k), JobFunnel (2.2k archived), boss-agent-cli (1.6k), boss-zhipin-scraper (1.1k)
**Tier 3 (100–1k):** jobsync (854), EasyApplyJobsBot (804), career-ops-plugin (463), resume_render (412), jobspy-api (376), get-job.skill (348), freehire (337), interview-skills (272), jobclaw (208), lib_resume_builder_AIHawk (193), Job-apply-AI-agent (177), Job_search_agent (171 archived), jobseek (167), job-hunter (150), LinkedIn-AI-Job-Applier-Ultimate (147)
**Tier 4 (<100 / archived / no license):** AutoApply (111), autoapplycv (73), AutoApply-AI-Agentic-... (65), AutoApplyMax (58), JobScout (47 stale), ai-job-scraper (44), go-get-jobs (40), auto-apply-bot (34), JobSentinel (20), job_agentic (3), PunithVT/career-ops (2)

### Chapter 4 — Tiered Adoption Strategy

**Tier 1 — absorb first (capability surface):**

- **career-ops** — plugin registry + per-provider LLM runners + ~120-capability script catalog (CV builder, cover-letter, ATS scanner, weekly digest, dashboard builder, followup cadence, skill extractor, salary gap) + test patterns + Dockerfile + 17 CI workflows.
- **MadsLorentzen** — drafter→reviewer two-agent loop + LaTeX CV pipeline + per-board skill pattern + /setup profile ingestion + salary benchmarking + upstream-watch.yml.
- **AIHawk** — question-answering module + LinkedIn Easy Apply Selenium flow (re-implemented on Patchright). Skip its architecture (single-script monolith, JSON persistence, no tests, no Docker, OpenAI-locked).

**Tier 2 — fill specific gaps:**

- **JobSpy** — vendor as pip dep (highest leverage in entire plan).
- **job-ops** — reference architecture (orchestrator, extractors, visa-sponsor-providers — unique). NOASSERTION — read for inspiration, do not vendor.
- **Auto_job_applier_linkedIn** — LinkedIn-specific resilience patterns.
- **boss-agent-cli** — JSON-envelope output pattern (make JoBot callable as agent-tool).
- **boss-zhipin-scraper** — CDP session-reuse stealth pattern.

**Tier 3 — selectively absorb:** jobsync (dashboard UX), replyre/job-hunter (outreach), interview-skills (FAANG mock), feder-cr resume libs (rendering reference).

**Tier 4 — skip:** JobFunnel (archived), algsoch/job_agentic (no license, Ollama-only), JobScout (stale), EasyApplyJobsBot (no license), imon333 (no license, AIHawk supersedes), all Chrome extensions, auto-apply-bot (Gupy niche).

#### License Compliance Decision Tree

| Source license | Action | Notes |
|---|---|---|
| AGPL-3.0 | Vendor directly (with attribution) | Same license. AIHawk is AGPL. |
| GPL-3.0 | Vendor directly | One-way compatible. sreekarrs/JobSearch-Agent is GPL-3.0. |
| Apache-2.0 / MIT / BSD | Vendor directly | Permissive. JobSpy, career-ops, GodsScion, MadsLorentzen all MIT. |
| MPL-2.0 | Vendor with care | File-level copyleft. Lifted files remain MPL. |
| Unlicense / CC0 | Vendor freely | Public domain. |
| NOASSERTION | **Reference only — DO NOT VENDOR** | Risky. job-ops is NOASSERTION. |
| None (no LICENSE file) | **Reference only — DO NOT VENDOR** | All Rights Reserved. |

**Legally untouchable (do not vendor code):**
- wodsuz/EasyApplyJobsBot (804★) — NOASSERTION
- imon333/Job-apply-AI-agent (177★) — None
- replyre/job-hunter (150★) — None
- beatwad/LinkedIn-AI-Job-Applier-Ultimate (147★) — None
- jennifer88huang/interview-skills (272★) — None
- algsoch/job_agentic (3★) — None
- DaKheera47/job-ops (3,840★) — NOASSERTION

#### Recommended Adoption Sequence

| Week | Phase | Exit criterion |
|---|---|---|
| 1–2 | Vendor JobSpy as pip dep | `jobot scrape linkedin` returns ≥50 real postings |
| 3–6 | Port career-ops capability modules | `jobot apply --dry-run` produces tailored resume + cover letter |
| 7–10 | Port MadsLorentzen drafter→reviewer + LaTeX | `jobot resume tailor --jd <url>` produces ATS-safe PDF |
| 11–14 | Port AIHawk question-answering + Easy-Apply | `jobot apply <job-id>` completes real LinkedIn Easy Apply |
| 15+ | Selectively absorb Tier-3 single-capability | Each module has pytest suite + integration test |

---

## Part II — Target Architecture

### Chapter 5 — Target Architecture Overview

**Layer map:**

| Layer | Component | Examples | Owns |
|---|---|---|---|
| L1 — User Surface | Typer + rich CLI | `jobot scrape / apply / tracker / digest / plugin / config / doctor` | Argument parsing, output formatting |
| L2 — Orchestrator | Async task-graph engine | TaskGraph, Saga, Checkpoint, Quarantine | Task decomposition, parallelism, retry, idempotency |
| L3 — Capability Modules | 12 module packages | `scrapers/`, `resume/`, `coverletter/`, `apply/`, `interview/`, `tracker/`, `career/`, `outreach/`, `scheduler/` | Domain logic |
| L4 — Cross-cutting Services | 8 service planes | ModelRouter, BrowserPool, StoragePlane, PluginRegistry, PolicyEngine, TracingPlane, SkillExtractor, VectorMemory | Infrastructure |
| L5 — External Surfaces (Adapters) | Adapter registry | LinkedInAdapter, GreenhouseAdapter, LeverAdapter, JobSpyAdapter | Board-specific quirks |
| L6 — Storage & Secrets | 3-tier persistence | SQLite WAL + Fernet blob store + OS keyring | Durable state, encrypted secrets |
| L7 — Observability | Tracing + alerts + dashboard | OpenTelemetry spans, weekly digest | Trace trajectories, alert on anomalies |

**Design patterns:**

- **Strategy (LLMProvider)** — runtime provider swap
- **Factory (BoardAdapterRegistry)** — new adapters via plugin
- **Adapter (board-specific quirks)** — translate canonical types
- **Saga (multi-step apply)** — atomicity with compensating actions
- **State Machine (ASP 12-phase)** — event-sourced application status
- **Circuit Breaker** — per-adapter failure isolation
- **Idempotency Key** — safe retries
- **Plugin (user-installed capabilities)** — community extension
- **Observer (tracing)** — every task emits spans
- **Repository** — modules never touch SQLite directly

### Chapter 6 — AI Provider Abstraction Layer (ModelRouter v2)

Six provider classes, twelve concrete instances. Gemini default. See [SETUP.md Chapter 5](./SETUP.md#5-ai-provider-api-keys-all-6-supported-providers) for full setup.

```python
# jobot/llm/base.py
class LLMProvider(ABC):
    name: str
    default_model: str
    pricing: dict[str, ProviderPricing]

    @abstractmethod
    async def complete(self, messages: list[Message], model: str | None = None,
                       temperature: float = 0.7, max_tokens: int = 2048,
                       tools: list[ToolSpec] | None = None,
                       timeout_s: float = 60.0) -> LLMResponse: ...

    @abstractmethod
    async def stream(self, messages, **kw) -> AsyncIterator[str]: ...

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int,
                      model: str | None = None) -> float: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

```python
# jobot/llm/router.py
PROVIDER_REGISTRY = {
    'gemini':     GeminiProvider,
    'openai':     OpenAIProvider,
    'anthropic':  AnthropicProvider,
    'openrouter': lambda: OpenAICompatProvider(base_url='https://openrouter.ai/api/v1'),
    'groq':       lambda: OpenAICompatProvider(base_url='https://api.groq.com/openai/v1'),
    'together':   lambda: OpenAICompatProvider(base_url='https://api.together.xyz/v1'),
    'ollama':     lambda: OpenAICompatProvider(base_url=os.environ.get('OLLAMA_BASE_URL','http://localhost:11434/v1')),
    'vllm':       lambda: OpenAICompatProvider(base_url=os.environ.get('VLLM_BASE_URL')),
    'mistral':    MistralProvider,
    'cohere':     CohereProvider,
    'bedrock':    BedrockProvider,
    'vertex':     VertexProvider,
}
```

Switch provider at runtime: `jobot config set llm.default_provider anthropic`

### Chapter 7 — Browser Automation Layer

Patchright (stealth Playwright) primary. CDP session-reuse alternative (from boss-zhipin-scraper). BrowserPool with persistent contexts. Named actions (not one-off DOM scripts). Captcha solver hook (2captcha / human fallback). Selector healing. Preview-before-commit + screenshot evidence on every risky action.

### Chapter 8 — Storage & State Plane

- **Tier 1 (SQLite WAL):** jobs, applications, events, traces, spans
- **Tier 2 (Fernet blob store):** resume PDFs, cover letters, full JDs (encrypted at rest)
- **Tier 3 (OS keyring):** LLM API keys, board credentials, Fernet master key

Vector memory for semantic dedup of job postings (cosine sim > 0.92 = dup).

### Chapter 9 — Task Graph & Orchestrator

TaskGraph (acyclic, typed, checkpointable). Saga (multi-step transactions with compensating actions). Idempotency keys on every side effect. Quarantine/dead-letter for poison work. Tracing spans per task.

### Chapter 10 — Plugin & Adapter Registry

Two-tier extension system. **Adapters** = first-party board integrations (LinkedIn, Greenhouse, Lever). **Plugins** = user-installable capability modules with audit + install flow.

### Chapter 11 — Security, PII & Policy Engine

PII masker (regex + LLM-assist). Policy engine with caps (daily/weekly apply + cost). Audit log (append-only). Every side effect has idempotency key. Worked example: 51st application blocked because daily_cap=50.

---

## Part III — Capability Modules

### Chapter 12 — Multi-Source Job Scraper (JobSpy integration)

Vendor `speedyapply/JobSpy` as pip dep. Build `JobSpyAdapter` wrapping JobSpy's `scrape_jobs()` behind JoBot's circuit breaker + dedup. Direct-API adapters for Greenhouse, Lever, Ashby. Career-page scanner (YAML-driven, 150+ sites). Two-tier dedup (hash + vector).

```toml
# pyproject.toml
[project]
dependencies = [
    "jobspy>=0.4.0",
]
```

### Chapter 13 — Resume Tailoring (Drafter-Reviewer + LaTeX)

Two-agent loop: drafter LLM generates tailored CV → reviewer LLM critiques with A-F rubric → iterate until score ≥ 3.5 or max_iterations=3. LaTeX rendering via lualatex + xelatex. ATS parseability check via `pdftotext`. Three templates (default, modern, classic).

### Chapter 14 — Cover-Letter Generator

Single-pass LLM call with 5 tone presets (classic, narrative, technical, brief, enthusiastic). Length caps. Per-job tuning via JD embedding similarity.

### Chapter 15 — Auto-Apply Engine

13-step saga with compensating actions. LinkedIn Easy Apply on Patchright. Direct-API apply for Greenhouse/Lever. Question-answering module (lifted from AIHawk, re-implemented behind ModelRouter). Human-in-the-loop checkpoint for sensitive submissions. Preview-before-commit with screenshot evidence.

### Chapter 16 — Interview Prep

Mock interview sessions (multi-turn). STAR-method answer coach. Question banks: FAANG behavioral, system design, technical. Lifted from career-ops `interview-prep/` + jennifer88huang/interview-skills.

### Chapter 17 — Application Tracking & Dashboard

ASP 12-phase state machine. Weekly digest email. Analytics dashboard (terminal + HTML export). Funnel velocity, rejection latency, response rate by board. Lifted from career-ops + jobsync.

### Chapter 18 — Career Analytics & Salary Benchmarking

Levels.fyi + Built In salary scraper (24h cache). Skill-gap analysis (extract skills from saved JDs vs profile). Learning path recommendations.

### Chapter 19 — Outreach & Cold-DM Generation

Profile-driven YAML presets (FAANG senior, startup founding, quant finance). LinkedIn people-search URL generator. DM templates. SMTP email sender. Re-implemented from replyre/job-hunter (no license — must re-implement).

### Chapter 20 — Scheduler & Daily Loop

Four modes: scan-only, apply-only, digest-only, full-loop. Cron-friendly. Modes lifted from career-ops.

```cron
# Daily full-loop at 9am
0 9 * * * /usr/local/bin/jobot loop full-loop --profile default --max-apply 10
# Weekly digest Monday 8am
0 8 * * 1 /usr/local/bin/jobot loop digest --profile default
# Reset daily caps at midnight UTC
0 0 * * * /usr/local/bin/jobot policy reset-daily --profile default
```

---

## Part IV — Phased Migration Roadmap

### Phase 0 — Audit & Cleanup (Week 1)

- Move all `*.md` planning docs from root to `docs/history/`
- Delete stub files in `jobot/adapters/`
- Run full test suite, record baseline
- Document ASP 12-phase in `docs/asp.md`
- Freeze public interfaces
- Run `ruff + mypy strict` clean

**Exit:** repo root clean, 100% tests pass, mypy strict clean.

### Phase 1 — Provider Abstraction + Config (Weeks 2–3)

- Implement OpenAICompatProvider, MistralProvider, CohereProvider, BedrockProvider, VertexProvider
- Add `pricing.yaml` with per-model cost data
- Land ModelRouter v2 with cost-aware routing + fallback chain + daily cost cap
- Land profiles/ YAML schema + secrets.py OS-keyring integration
- Add `jobot config get/set/show` + `jobot doctor` CLI commands
- Tests for every provider (mock HTTP) + integration tests against real APIs

**Exit:** `jobot doctor` passes with ≥1 provider configured. `jobot config set` round-trips. All provider tests pass.

### Phase 2 — Scraper Merge (Weeks 4–5)

- Add `jobspy>=0.4.0` to `pyproject.toml`
- Implement `JobSpyAdapter` wrapping JobSpy behind circuit breaker + dedup
- Implement GreenhouseAdapter + LeverAdapter (direct JSON API)
- Implement CareerPageScanner with YAML-driven 150+ site config
- Vector dedup service (cosine sim > 0.92)
- Add `jobot scrape <board>` CLI command

**Exit:** `jobot scrape linkedin --keywords 'senior backend' --location 'San Francisco' --limit 50` returns 50+ real postings. Dedup reduces repost rate by ≥80%.

### Phase 3 — Resume + Cover-Letter + Auto-Apply (Weeks 6–9)

- Implement Drafter + Reviewer with A-F rubric scoring
- Implement LaTeX rendering (lualatex + xelatex + pdftotext ATS check)
- Land 3 LaTeX templates (default, modern, classic) via Jinja2
- Implement CoverLetterGenerator with 5 tone presets
- Implement QuestionAnswerer (from AIHawk) behind ModelRouter
- Implement LinkedInEasyApplySaga on Patchright
- Implement GreenhouseApplyAdapter + LeverApplyAdapter (direct API)
- Implement ApplyOrchestrator with saga + compensating actions + idempotency keys
- Preview-before-commit + human-in-the-loop checkpoint

**Exit:** `jobot apply --dry-run <job-id>` produces tailored resume PDF + cover letter with ATS score ≥ 0.85. Real apply to test Greenhouse posting succeeds.

### Phase 4 — ATS, Analytics, Plugins, Docker (Weeks 10–13)

- InterviewPrep module (mock session + STAR coach)
- TrackerDashboard (terminal + HTML export)
- WeeklyDigest email sender
- CareerAnalytics (salary + skill-gap)
- Outreach module (URL gen + DM templates + SMTP)
- Scheduler with 4 modes
- PluginInstaller + PluginManifest schema + audit flow
- Dockerfile (multi-stage) + docker-compose.yml
- CI hardening: CodeQL workflow, SBOM generation, signature-CI

**Exit:** `docker compose up -d` brings up working stack. `jobot plugin install <git-url>` + audit succeeds. Weekly digest arrives in inbox.

### Risks, Mitigations & License Compliance

18 risks across 4 categories (legal, technical, operational, product). Top 5:

1. **Vendoring from NOASSERTION repo** → Use License Compliance Decision Tree; re-implement, never vendor.
2. **LinkedIn detects Patchright** → Stealth patches, session reuse via CDP, named-action pattern, slow-mode with realistic delays, human-in-the-loop fallback.
3. **JobSpy selectors break** → Pin version, daily health-check, alert on circuit-breaker opening.
4. **LLM rate limits** → Fallback chain, circuit breaker per provider, daily cost cap.
5. **Saga left half-applied state** → Compensating actions on every step, checkpoint after every step, quarantine failed sagas.

---

## Appendix A — Full Source Repository Star Inventory

| # | Repo | Stars | Lang | License | Tier |
|---:|---|---:|---|---|:-:|
| 1 | santifer/career-ops | 63,659 | JavaScript | MIT | 1 |
| 2 | MadsLorentzen/ai-job-search | 31,411 | TypeScript | MIT | 1 |
| 3 | feder-cr/Jobs_Applier_AI_Agent_AIHawk | 30,159 | Python | AGPL-3.0 | 1 |
| 4 | speedyapply/JobSpy | 4,072 | Python | MIT | 2 |
| 5 | DaKheera47/job-ops | 3,840 | TypeScript | NOASSERTION | 2 |
| 6 | GodsScion/Auto_job_applier_linkedIn | 2,688 | Python | MIT | 2 |
| 7 | PaulMcInnis/JobFunnel (ARCHIVED) | 2,178 | Python | MIT | 2 |
| 8 | can4hou6joeng4/boss-agent-cli | 1,558 | Python | MIT | 2 |
| 9 | eatmoreduck/boss-zhipin-scraper | 1,094 | Python | MIT | 2 |
| 10 | Gsync/jobsync | 854 | TypeScript | MIT | 3 |
| 11 | wodsuz/EasyApplyJobsBot | 804 | Python | NOASSERTION | 3 |
| 12 | andrew-shwetzer/career-ops-plugin-... | 463 | HTML | MIT | 3 |
| 13 | feder-cr/resume_render_from_jd | 412 | Python | MIT | 3 |
| 14 | rainmanjam/jobspy-api | 376 | Python | (check) | 3 |
| 15 | agentenatalie/get-job.skill | 348 | Python | NOASSERTION | 3 |
| 16 | strelov1/freehire | 337 | Go | MIT | 3 |
| 17 | jennifer88huang/interview-skills | 272 | JavaScript | None | 3 |
| 18 | slothsheepking/jobclaw | 208 | ? | — | 3 |
| 19 | feder-cr/lib_resume_builder_AIHawk | 193 | Python | MIT | 3 |
| 20 | imon333/Job-apply-AI-agent | 177 | Python | None | 3 |
| 21 | surapuramakhil-org/Job_search_agent (ARCHIVED) | 171 | Python | AGPL-3.0 | 3 |
| 22 | colophon-group/jobseek | 167 | Python | ? | 3 |
| 23 | replyre/job-hunter | 150 | Python | None | 3 |
| 24 | beatwad/LinkedIn-AI-Job-Applier-Ultimate | 147 | Python | None | 3 |
| 25 | Liam-Frost/AutoApply | 111 | Python | ? | 4 |
| 26 | tmwclaxton/autoapplycv | 73 | JavaScript | NOASSERTION | 4 |
| 27 | Rayyan9477/AutoApply-AI-Agentic-... | 65 | Python | ? | 4 |
| 28 | Azoo92i/AutoApplyMax | 58 | JavaScript | ? | 4 |
| 29 | krishnavalliappan/JobScout (STALE) | 47 | Python | None | 4 |
| 30 | BjornMelin/ai-job-scraper | 44 | Python | MIT | 4 |
| 31 | kbhujbal/go-get-jobs | 40 | Go | None | 4 |
| 32 | LuisMIguelFurlanetteSousa/auto-apply-bot | 34 | TypeScript | MIT | 4 |
| 33 | cboyd0319/JobSentinel | 20 | TypeScript | MIT | 4 |
| 34 | algsoch/job_agentic | 3 | Python | None | 4 |
| 35 | PunithVT/career-ops | 2 | JavaScript | ? | 4 |
| — | **aryansinghnagar/JoBot (TARGET)** | **0** | **Python** | **AGPL-3.0** | — |

**Repos that could not be located:** feder-cr/AIHawk (the original) — 404; surapuramakhil-org/AI-job-apply-agent — 404; Nexloop/JobScan-AI — 404; SurferMatt/job-application-automator — 404; aiagentjobseeker — 404; AutoJobr / JobLLM / JobPilot-AI — no GitHub results.

---

## Appendix B — Glossary

40+ terms. See full glossary in [PDF Appendix B](./JoBot_Merge_Plan.pdf). Key terms:

- **ASP** — Application State Protocol (12-phase state machine)
- **Adapter** — Board-specific integration (LinkedIn, Greenhouse, etc.)
- **ModelRouter** — Provider-neutral LLM abstraction (Strategy pattern)
- **Saga** — Multi-step transaction with compensating actions
- **Patchright** — Stealth fork of Playwright
- **Fernet** — Symmetric authenticated encryption for blob store
- **Idempotency Key** — Hash enabling safe retries
- **Tier (1/2/3/4)** — Repo prioritization by stars + maintenance

---

## Next Steps

1. **Read [SETUP.md](./SETUP.md)** for installation and provider setup.
2. **Run `jobot doctor`** after install to verify environment.
3. **Start Phase 0** of the migration roadmap (audit + cleanup).
4. **Open issues** on the JoBot GitHub repo for any specific module you'd like to prioritize.
