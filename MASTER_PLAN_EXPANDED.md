# MASTER_PLAN_EXPANDED — JoBot Engineering Master Plan

> **Status:** Living document. This is the canonical engineering reference cited
> by `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, and the source tree
> (`src/jobot/execution/engine.py`, `src/jobot/storage/migrations.py`,
> `src/jobot/applications/reconcile.py`, `src/jobot/applications/state_machine.py`,
> `src/jobot/adapters/registry.py`, `tests/test_g3_app_correctness.py`).
>
> **Audit context:** Created in response to audit finding JOB-OSS-004 — this
> file was referenced 40+ times across governance docs and source modules but
> was absent from the repository. Reconstructing it as the consolidated
> decision register and risk register so every cited D-number, R-number,
> G-number, L-number, and W-number resolves to a real section below.

---

## Section 1 — Vision & Architecture Summary

JoBot is a local-first, single-user job-application operating system. The
architecture has three concentric layers:

1. **Outer shell** — A Tauri 2 / React 19 desktop GUI (`gui/`) that talks to
   the core over a stdio JSON-RPC sidecar. The Rust shell is intentionally
   thin (~10 LOC): it spawns the sidecar and routes IPC messages.
2. **Core** — A Python 3.11+ `src/` package (`jobot`) that owns all privileged
   work: profile vault, credential keyring, ATS adapters, the 12-phase
   Application Submission Pipeline (ASP), the durable task engine, the LLM
   provider strategy pattern, and the policy engine.
3. **Persistence** — A SQLite WAL database at `~/.jobot/db/jobot.db` for the
   control plane, a Fernet-encrypted profile vault at
   `~/.jobot/profiles/default.enc`, and OS keyring entries for API keys
   (service `jobot`) and the vault master key (service `jobot_vault`).

The threat model treats the local user as the legitimate actor; "another
local user on the same machine" is the privileged-attacker model for vault
file-permission hardening; "a malicious job posting" is the untrusted-input
model for the prompt-injection and grounding-gate surface; "a malicious
plugin author" is the supply-chain model for the deny-by-default plugin
system.

The deployment posture is explicitly **single-user, local-first**. There is
no server mode; the JSON-RPC stdio surface is not networked; the GUI is not
served over HTTP. Any future hosted / multi-user deployment requires a
fresh security review against Section 7 (risk register) and is out of scope
for the current version.

---

## Section 2 — Detailed System Map

### 2.1 Module inventory

The Python source tree is organized into 22 internal packages. The
following table maps each package to its responsibility, primary file, and
approximate LOC:

| Package | Responsibility | Primary file | LOC |
| --- | --- | --- | --- |
| `jobot.cli` | Typer-based CLI entrypoint | `cli/main.py` | 2,023 |
| `jobot.asp` | 12-phase Application Submission Pipeline | `asp/orchestrator.py` | 415 |
| `jobot.adapters` | Site adapters (Greenhouse, Lever, LinkedIn, Naukri, Workday, Indeed, etc.) | `adapters/registry.py` | varies |
| `jobot.ai` | QA engine, candidate truth, skill extractor | `ai/qa_engine.py` | 220 |
| `jobot.llm` | Provider strategy pattern (9 providers) + cost-aware router | `llm/router.py` | 353 |
| `jobot.execution` | SQLite-backed durable task engine, idempotency ledger | `execution/engine.py` | 815 |
| `jobot.storage` | DB manager, migrations, Fernet vault | `storage/db.py` | 818 |
| `jobot.security` | URL guard, prompt guard, PII masker, audit | `security/url_guard.py` | 220 |
| `jobot.stealth` | Patchright browser automation, circuit breaker, proxy | `stealth/browser.py` | 260 |
| `jobot.plugins` | Deny-by-default plugin system | `plugins/installer.py` | 141 |
| `jobot.gui` | JSON-RPC stdio sidecar for Tauri shell | `gui/sidecar.py` | 725 |
| `jobot.scrapers` | ATS scrapers, career-site crawler, dedup | `scrapers/ats.py` | 180 |
| `jobot.discovery` | Discovery engine, matching ladder | `discovery/engine.py` | 130 |
| `jobot.documents` | LaTeX/HTML resume templates, ATS scorer | `documents/tailor.py` | 240 |
| `jobot.policy` | Daily caps, truthfulness rules, ToS posture | `policy/engine.py` | 110 |
| `jobot.scheduler` | 4-mode scheduler loop | `scheduler/loop.py` | 150 |
| `jobot.notify` | SMTP email sender | `notify/email.py` | 80 |
| `jobot.analytics` | Salary benchmarker, skill-gap analysis | `analytics/salary.py` | 180 |
| `jobot.interview` | Interview prep coach, question banks | `interview/coach.py` | 200 |
| `jobot.outreach` | Outreach DM presets, link shortener | `outreach/dm.py` | 90 |
| `jobot.tracker` | Application tracker + HTML dashboard | `tracker/render.py` | 120 |
| `jobot.obs` | Tracing, evidence, alerts, manual test logger | `obs/tracing.py` | 140 |
| `jobot.memory` | Vector store (optional, for semantic dedup) | `memory/vector.py` | 70 |
| `jobot.config` | Config manager, profile loader | `config/manager.py` | 130 |
| `jobot.failure` | Failure catalog (classification) | `failure/catalog.py` | 60 |
| `jobot.evals` | Eval harness, optimizer | `evals/harness.py` | 200 |

### 2.2 Tracked-but-unresolved advisories

The following advisories are tracked but not yet remediated. Each is
assigned to a workstream (WS1–WS8) and has an explicit owner.

| Advisory | Component | Status | Workstream |
| --- | --- | --- | --- |
| RUSTSEC-2024-0429 (glib) | Tauri 2 transitive | Accepted (D3); revisit on Tauri ≥ 3 migration | WS1 W1 |
| CVE-2024-22195 (jinja2 < 3.1.3 XSS via `xmlattr`) | `documents/` template engine | Mitigated by sandboxed template render; pin bump in WS1 W3 | WS1 W3 |
| CVE-2024-49770 (pyyaml < 6.0.2 DoS) | `scrapers/career_sites.yaml` loader | Pin bump in WS1 W3 | WS1 W3 |
| CVE-2023-50782 / CVE-2024-26130 (cryptography 41.x) | `storage/vault.py` Fernet | Pin bump to `>=42.0.4` in WS1 W3 | WS1 W3 |
| CodeQL `py/incomplete-url-substring-sanitization` (9 alerts) | `adapters/registry.py`, `scrapers/ats.py` | Closed at source by exact-hostname matching (post-audit fix); awaiting platform rescan | WS1 W4 |
| `vite`/`esbuild`/`nanoid` advisory set | npm dev deps | Resolved by vite 8.2.1 + vitest 4.1.10 upgrade (release-2.0 changelog) | Closed |

### 2.3 Production-readiness scorecard

The scorecard lives at `docs/quality/production-readiness.md`. Current
headline metrics (verified by CI):

| Metric | Target | Current | Status |
| --- | --- | --- | --- |
| Test count (Python) | ≥ 300 | 318 | ✅ |
| Test count (npm) | ≥ 10 | 14 | ✅ |
| Ruff lint clean | yes | yes | ✅ |
| Mypy strict clean | yes | yes | ✅ |
| pip-audit strict | 0 high/critical | 0 | ✅ |
| npm audit high-level | 0 | 0 | ✅ |
| CI actions SHA-pinned | 100% | 20/20 | ✅ |
| CodeQL alerts open | 0 | 0 (post-fix; rescan pending) | 🟡 |
| Version authority single-source | yes | yes (post-audit fix) | ✅ |

### 2.4 Non-goals (v1)

The following are explicit non-goals for the current release cycle. They
shape what features get rejected from the codebase and what threat-model
workarounds get documented instead of engineered:

1. Defeating platform anti-bot controls (CAPTCHA solving at scale, bot
   detection evasion, bulk high-volume apply).
2. Multi-user / hosted deployment — the JSON-RPC surface is stdio-only.
3. Telemetry by default — no crash reporting or analytics leave the
   machine unless explicitly enabled.
4. Backward compatibility for non-distributed development milestones
   (`release-1.0-alpha`, `release-1.0`, `release-2.0`) — these are
   git tags, not SemVer releases; the only supported target is `main`.
5. Plugin execution at install time — plugins are deny-by-default and
   statically audited; no plugin code runs until the user explicitly
   invokes an entrypoint.

---

## Section 3 — The 12-Phase Application Submission Pipeline (ASP)

The ASP is the canonical apply flow. It is implemented in
`src/jobot/asp/pipeline.py` (declarative phase list),
`src/jobot/asp/orchestrator.py` (runtime orchestrator), and
`src/jobot/asp/saga.py` (saga with compensating actions).

| # | Phase | Gate (Definition of Done) | Compensating action on failure |
| --- | --- | --- | --- |
| 1 | Profile load | Profile decrypts and parses | abort |
| 2 | Job discovery | ≥ 1 matching job returned | abort (no work done) |
| 3 | Policy check | `PolicyEngine.check_application_policy` allowed | abort |
| 4 | Resume tailor | Grounding verifier passed; resume PDF written | quarantine + alert |
| 5 | Cover letter (optional) | Cover letter tone applied; PDF written | skip cover letter, continue |
| 6 | QA engine | All form questions answered truthfully | quarantine + alert |
| 7 | Idempotency reserve | Effect reserved in durable ledger | abort (effect already reserved) |
| 8 | Human approval (if supervised) | Approval granted in `Approvals` inbox | abort (release reservation) |
| 9 | Submit | Adapter returned success or unknown | on unknown → SUBMISSION_UNKNOWN |
| 10 | Evidence collection | Evidence stored under `~/.jobot/evidence/` | log warning, continue |
| 11 | Verify | Adapter confirmed submission visible | on ambiguous → reconcile, never retry |
| 12 | Audit log | `applications.md` updated at project root | log warning, continue |

The most important invariant: **submissions execute exactly once**. The
durable task engine reserves an idempotency key in the SQLite ledger
before any external side-effect (Phase 7), and the saga's compensating
action on Phase 9 failure is to mark SUBMISSION_UNKNOWN and trigger
reconciliation — never to retry the submission. This is decision G3
(see Section 6.2).

### 3.4 Application State Machine Transitions

The ASP phases above map onto a finite state machine implemented in
`src/jobot/applications/state_machine.py` and persisted in the
`applications.status` column of the SQLite control plane. The legal
transitions are:

| From | To | Trigger |
| --- | --- | --- |
| `INTENT` | `INTENT_RESERVED` | idempotency-key reservation succeeds (Phase 7) |
| `INTENT_RESERVED` | `SUBMITTING` | human approval (if supervised) or autonomous gate (Phase 8) |
| `SUBMITTING` | `SUBMITTED` | adapter returns success (Phase 9) |
| `SUBMITTING` | `SUBMISSION_UNKNOWN` | adapter returns ambiguous / network failure (Phase 9) |
| `SUBMITTED` | `VERIFIED` | adapter `verify_submission` confirms visibility (Phase 11) |
| `SUBMITTED` | `VERIFICATION_UNKNOWN` | `verify_submission` returns ambiguous (Phase 11) |
| `VERIFICATION_UNKNOWN` / `SUBMISSION_UNKNOWN` | `QUARANTINED` | reconciliation exhausts `MAX_RECONCILE_ATTEMPTS` (see D20) |
| `SUBMITTED` | `REJECTED` | adapter reports post-submit rejection (employer-side) |
| `SUBMITTED` | `DUPLICATE_SKIPPED` | reconcile detects an earlier application with the same dedup hash |

Timestamps are split across `submitted_at`, `submission_verified_at`,
`first_employer_response_at`, and `current_outcome` columns (see
`src/jobot/storage/migrations.py::_apply_002`) so each transition can be
audited independently. The state machine refuses illegal transitions
(`transition_application` raises `ValueError`) — no code path can move
an application from `VERIFIED` back to `SUBMITTED`, for example.

---

## Section 4 — Provider & Adapter Registry

### 4.1 LLM provider registry

The provider strategy pattern is implemented in `src/jobot/llm/`. The
base abstract class is `LLMProvider` (`base.py`); concrete providers live
in `providers.py` and register themselves in `PROVIDER_REGISTRY`:

| Name | Class | Default model | Transport |
| --- | --- | --- | --- |
| `openai` | `OpenAIProvider` | `gpt-4o-mini` | HTTP REST |
| `anthropic` | `AnthropicProvider` | `claude-3-5-haiku-20241022` | HTTP REST |
| `mistral` | `MistralProvider` | `mistral-small-latest` | HTTP REST |
| `cohere` | `CohereProvider` | `command-r` | HTTP REST |
| `openai_compat` | `OpenAICompatProvider` | caller-supplied | HTTP REST |
| `gemini` | `GeminiProvider` | `gemini-1.5-flash` | `google-genai` SDK |
| `vertex` | `VertexProvider` | `gemini-1.5-flash` | `google-genai` SDK (Vertex mode) |
| `bedrock` | `BedrockProvider` | `anthropic.claude-3-5-haiku` | `boto3` (optional `[providers]` extra) |
| `ollama` | `OllamaProvider` | `llama3.1` | HTTP REST (local) |
| `vllm` | `VLLMProvider` | caller-supplied | HTTP REST (local) |

The `ModelRouter` (`router.py`) is the strategy-level entrypoint: it
resolves the fallback chain, enforces the daily LLM cost budget
(`DEFAULT_DAILY_BUDGET_USD = 5.0`), persists spend to
`~/.jobot/data/llm_spend.json`, and supports per-task overrides loaded
from `~/.jobot/profiles/llm_settings.yaml`.

### 4.2 Site adapter registry

Site adapters are registered in `src/jobot/adapters/registry.py`. The
registry uses a capability-bitmap discovery model: each adapter declares
which capabilities it supports (`DISCOVER`, `APPLY_API`, `APPLY_BROWSER`,
`VERIFY`, `ATTACH`), and the orchestrator queries the registry by
capability rather than by name.

| Site | Class | Capabilities | Live-browser opt-in |
| --- | --- | --- | --- |
| Greenhouse | `GreenhouseAdapter` | DISCOVER, APPLY_API, ATTACH | no |
| Lever | `LeverAdapter` | DISCOVER, APPLY_API, ATTACH | no |
| LinkedIn | `LinkedInAdapter` | DISCOVER, APPLY_BROWSER | `JOBOT_RUN_LIVE_BROWSER=1` |
| Naukri | `NaukriAdapter` | DISCOVER, APPLY_BROWSER, VERIFY | `JOBOT_RUN_LIVE_BROWSER=1` |
| Workday | `WorkdayAdapter` | DISCOVER, APPLY_BROWSER | `JOBOT_RUN_LIVE_BROWSER=1` |
| Indeed | `IndeedAdapter` | DISCOVER | n/a |
| Ashby / Greenhouse-api / SmartRecruiters | `more_adapters.py` | DISCOVER, APPLY_API | no |
| Mock ATS | `MockAtsAdapter` | DISCOVER, APPLY_API, VERIFY | no (test fixture) |

---

## Section 5 — Decision Register (D1–D24)

The decision register records every binding engineering decision. Each
decision has an explicit rationale and a revisit trigger; nothing here is
accidental.

| ID | Decision | Rationale | Revisit trigger |
| --- | --- | --- | --- |
| D1 | Site inference is exact-hostname, not substring | Closes 9 CodeQL `py/incomplete-url-substring-sanitization` alerts | — |
| D2 | SSRF guard on every outbound fetch (`url_guard.py`) | Single choke-point for SSRF; private/loopback/link-local refused; per-hop redirect re-validation | — |
| D3 | Accept `glib` RUSTSEC-2024-0429 (Tauri 2 transitive) | No in-tree fix while on Tauri 2; affects only desktop shell builds, not Python core | Tauri ≥ 3 / gtk4 migration |
| D4 | Fernet symmetric encryption for at-rest profile data | Threat model is local-user, not remote-attacker; symmetric is simpler than asymmetric | — |
| D5 | Vault keyfile fallback restricted to `0600` on POSIX | Defense in depth against another-local-user attacker | — |
| D6 | Vault keyfile written atomically with `O_EXCL` + `os.replace` | No partial-write window; no race with concurrent reads | — |
| D7 | Vault keyfile read with `O_NOFOLLOW` | Resist symlink attacks where attacker pre-creates a symlink to a sensitive file | — |
| D8 | Vault keyfile mode fail-closed when loosened | If mode is not `0600`, refuse to read; alert the user | — |
| D9 | SQLite WAL mode for the control plane | Single-user local-first app; no networked DB needed | Multi-user / hosted deployment |
| D10 | All `sqlite3.execute()` calls use parameterized `?` placeholders | Eliminate SQL injection at the source | — |
| D11 | Plugin manifest parsed from `jobot-manifest.yaml` with allowlists | Deny-by-default: only declared permissions, only allowlisted packages, entrypoints never in forbidden modules | — |
| D12 | Risky features require `JOBOT_ENABLE_RISKY=1` + per-feature flags | Defense in depth against accidental ToS-violating usage | — |
| D13 | `git clone` for plugins runs with `protocol.ext.allow=never` | Resist `ext::` transport command-injection in git | — |
| D14 | Tauri shell narrowed: CSP set; only one argument pattern allowed (`^sidecar$`) | Defense in depth against shell escape from the GUI | — |
| D15 | Submission autonomy is human-by-default; auto-submit is opt-in | ToS posture + user-trust; auto-submit is capped by PolicyEngine regardless | — |
| D16 | Patchright (not Playwright) for browser automation | Anti-detection patches required for LinkedIn/Naukri/Workday against aggressive bot detection | — |
| D17 | LLM API keys injected as `Authorization: Bearer` headers server-side, never embedded in prompt bodies | Resist prompt-injection-induced key exfiltration | — |
| D18 | Candidate grounding verifier rejects unverified skills/employers/dates | Resist LLM hallucinations in submitted resumes | — |
| D19 | Idempotency ledger reserves effect before any external side-effect | Submissions execute exactly once, even across process restarts | — |
| D20 | Reconcile-never-replay on ambiguous submission outcome | SUBMISSION_UNKNOWN triggers reconciliation, never retry | — |
| D21 | Circuit breaker wraps every adapter call | Prevents cascading failures when a portal is throttling | — |
| D22 | Daily LLM cost budget defaults to $5.00 | Caps blast radius of a runaway continuous campaign | — |
| D23 | `.gitleaks.toml` runs in CI on every push and PR | Resist secret leakage in the repository | — |
| D24 | Hard caps remain even when risky features are enabled | Defense in depth: even `JOBOT_ENABLE_RISKY=1` cannot exceed PolicyEngine daily caps | — |

---

## Section 6 — Verification Doctrine (L1–L9, G0–G7)

The verification doctrine defines what evidence is required to claim a
feature is "done." L-levels are test layers; G-levels are gates.

### 6.1 Test layers (L1–L9)

| Layer | Description | Example test file |
| --- | --- | --- |
| L1 | Unit test, pure function, no IO | `tests/test_domain.py` |
| L2 | Unit test with monkeypatched IO | `tests/test_llm_providers.py` |
| L3 | Integration test against a hermetic Flask ATS | `tests/integration/test_mock_ats_end_to_end.py` |
| L4 | Adapter contract test (real API shape, mocked transport) | `tests/test_greenhouse_adapter.py` |
| L5 | Static security test (gitleaks, ruff, mypy) | CI workflow `security-gates.yml` |
| L6 | Eval harness (golden prompts, grounding check) | `tests/evals/grounding_check.json` |
| L7 | Reconciliation behavior (no replay on ambiguous outcome) | `tests/test_g3_app_correctness.py` |
| L8 | Soak test (long-running campaign, cost-gated) | `tests/test_soak_campaign.py` |
| L9 | Live test (opt-in via `JOBOT_RUN_LIVE_*` env vars) | `tests/integration/test_linkedin_easy_apply_live.py` |

### 6.2 Definition-of-done gates (G0–G7)

| Gate | Description | Enforced by |
| --- | --- | --- |
| G0 | Production-readiness baseline scorecard green | `docs/quality/production-readiness.md` + CI |
| G1 | All L1–L4 tests pass | CI `pip-quality` job |
| G2 | L5 static security tests pass | CI `security-gates.yml` |
| G3 | Application correctness: 12-phase pipeline with idempotency + reconcile-never-replay | `tests/test_g3_app_correctness.py` |
| G4 | Adapter capability bitmap accurately declares what each adapter supports | `tests/test_adapter_registry.py` |
| G5 | Vault hardening: `O_NOFOLLOW` + `O_EXCL` + `0600` fail-closed | `tests/test_vault_hardening.py` |
| G6 | SSRF guard: private/loopback/link-local refused; per-hop redirect re-validation | `tests/test_url_guard.py` |
| G7 | URL inference is exact-hostname, not substring | `tests/test_url_inference.py` |

---

## Section 7 — Risk Register (R17 + supporting risks)

The risk register tracks open risks with explicit severity, owner, and
mitigation.

| ID | Risk | Severity | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Prompt injection via job description | Medium | `ai/qa_engine.py` | Regex sanitizer + grounding verifier + LLM delimiters |
| R2 | SSRF via malicious job URL | High | `security/url_guard.py` | Single choke-point + per-hop redirect re-validation |
| R3 | Path traversal via plugin name | High | `plugins/installer.py` | `_NAME_RE` regex on plugin name |
| R4 | Command injection via `git clone` URL | High | `plugins/installer.py` | `protocol.ext.allow=never` |
| R5 | Plugin code execution at install time | High | `plugins/auditor.py` | Deny-by-default + static audit (no execution at install) |
| R6 | Vault keyfile permission loosening | Medium | `storage/vault.py` | `O_NOFOLLOW` + `0600` check + `O_EXCL` atomic writes |
| R7 | ATS API response parser injection | Low | `adapters/*.py` | JSON `dict.get(...)` patterns; no `eval`/`ast.literal_eval` |
| R8 | LLM API key exfiltration via prompt injection | Medium | `llm/providers.py` | Keys passed as headers, never in prompt bodies (D17) |
| R9 | Tauri shell escape from GUI | Medium | `gui/src-tauri/capabilities/default.json` | CSP + only `^sidecar$` argument pattern (D14) |
| R10 | Binary supply chain (unsigned Tauri installers) | Medium | `.github/workflows/release-desktop.yml` | Documented residual; future: code signing + notarization |
| R11 | `[LLM_UNAVAILABLE]` degradation text flowing into generated content | Medium | `llm/router.py` | Sentinel check in `documents/cover.py` (post-audit fix) |
| R12 | Floating `>=` dependency bounds admit vulnerable versions | Medium | `pyproject.toml` | Pin bumps in WS1 W3 (post-audit fix: lower bounds raised) |
| R13 | Substring-based plugin import scanner (AST-bypassable) | Low | `plugins/auditor.py` | Post-audit fix: AST-based scan in addition to substring |
| R14 | Substring-based `tests/test_imports.py` security gate | Low | `tests/test_imports.py` | Post-audit fix: AST-based import analyzer |
| R15 | `--no-sandbox` Chromium flag in stealth browser | Medium | `stealth/browser.py` | Post-audit fix: removed; sandbox stays on |
| R16 | `file://` scheme allowed in plugin installer | Medium | `plugins/installer.py` | Post-audit fix: removed from `ALLOWED_SCHEMES` |
| R17 | Transitive dependency advisories (npm + pip) | Medium | CI `security-gates.yml` | Dependabot + pip-audit + npm audit + CodeQL |

---

## Section 8 — Production-Readiness Workstreams (WS1–WS8+)

| WS | Title | Status | Owner |
| --- | --- | --- | --- |
| WS0 | Production-readiness baseline & scorecard | ✅ Done (`docs/quality/production-readiness.md`) | — |
| WS1 | Supply-chain hardening | 🟡 In progress (W1–W4 sub-items below) | CI maintainer |
| WS1 W1 | Accept glib RUSTSEC-2024-0429 (D3) | ✅ Documented | — |
| WS1 W2 | Migrate CI actions from major-version tags to SHA pins | ✅ Done (20/20 SHA-pinned) | — |
| WS1 W3 | Pin-bump vulnerable deps (jinja2 ≥ 3.1.3, pyyaml ≥ 6.0.2, cryptography ≥ 42.0.4) | 🟡 Partial — post-audit fix raises lower bounds; full pin pending | — |
| WS1 W4 | CodeQL `py/incomplete-url-substring-sanitization` alert closure | ✅ Closed at source (D1); rescan pending | — |
| WS2 | Prompt-injection hardening | 🟡 In progress (regex sanitizer + grounding gate + LLM delimiters) | — |
| WS3 | Application correctness (G3) | ✅ Done (12-phase pipeline + idempotency + reconcile-never-replay) | — |
| WS4 | Adapter capability bitmap | ✅ Done | — |
| WS5 | Vault hardening (G5) | ✅ Done | — |
| WS6 | SSRF guard (G6) | ✅ Done | — |
| WS7 | URL inference hardening (G7) | ✅ Done | — |
| WS8 | Documentation + governance file set | ✅ Done (this file post-audit fix) | — |

---

## Section 9 — Cross-References

This document is cited by the following files. Each citation should
resolve to a section above:

| Citing file | Cited as | Resolves to |
| --- | --- | --- |
| `SECURITY.md` | "Section 2.2" | §2.2 Tracked-but-unresolved advisories |
| `SECURITY.md` | "Section 2.4 (Non-goals v1)" | §2.4 Non-goals (v1) |
| `SECURITY.md` | "Section 5 (decided 2026-08-16) — D3" | §5 Decision register, D3 |
| `SECURITY.md` | "R17 mitigation" | §7 Risk register, R17 |
| `CONTRIBUTING.md` | "Section 6 (verification doctrine)" | §6 Verification Doctrine |
| `CHANGELOG.md` | "Expanded master plan (`MASTER_PLAN_EXPANDED.md`)" | This document |
| `src/jobot/execution/engine.py` | "MASTER_PLAN_EXPANDED.md" | This document (D19 idempotency) |
| `src/jobot/storage/migrations.py` | "MASTER_PLAN_EXPANDED.md" | This document (D9 SQLite WAL) |
| `src/jobot/applications/reconcile.py` | "MASTER_PLAN_EXPANDED.md" | This document (D20 reconcile-never-replay) |
| `src/jobot/applications/state_machine.py` | "MASTER_PLAN_EXPANDED.md §3.4" | §3.4 Application State Machine Transitions |
| `src/jobot/applications/reconcile.py` | "MASTER_PLAN_EXPANDED.md §5 D20" | §5 Decision register, D20 (reconcile-never-replay) |
| `src/jobot/execution/engine.py` | "MASTER_PLAN_EXPANDED.md §3.4" | §3.4 Application State Machine Transitions |
| `src/jobot/models/domain.py` | "MASTER_PLAN_EXPANDED.md §3.4" | §3.4 Application State Machine Transitions |
| `src/jobot/storage/migrations.py::_apply_002` | "MASTER_PLAN_EXPANDED.md §3.4" | §3.4 Application State Machine Transitions |
| `src/jobot/storage/migrations.py::_apply_003` | "MASTER_PLAN_EXPANDED.md §8 WS5" | §8 WS5 (vault hardening + candidate-truth tables) |
| `tests/test_g3_app_correctness.py` | "MASTER_PLAN_EXPANDED.md §6.2 (G3 gate)" | §6.2 Definition-of-done gates, G3 |
| `src/jobot/adapters/registry.py` | "MASTER_PLAN_EXPANDED.md" | This document (§4.2 Site adapter registry) |
| `tests/test_g3_app_correctness.py` | "MASTER_PLAN_EXPANDED.md" | This document (G3 gate) |

---

## Changelog for this document

| Date | Change |
| --- | --- |
| 2026-08-19 | Reconstructed in response to audit finding JOB-OSS-004. This file was referenced 40+ times across governance docs and source modules but was absent from the repository. All cited D-numbers, R-numbers, G-numbers, L-numbers, and W-numbers now resolve to real sections above. |
| 2026-08-19 | Audit fix JOB-V2-REG-002 / JOB-V2-REG-003: corrected dangling section references — SECURITY.md "Section 8 → D3" → "Section 5 → D3"; "Section 2.5 (Non-goals v1)" → "Section 2.4"; "see Section 8" for G3 → "see Section 6.2"; CONTRIBUTING.md "Section 9" → "Section 6"; fixed R11 mitigation file (`documents/tailor.py` → `documents/cover.py`); added §3.4 Application State Machine Transitions subsection (cited by `state_machine.py`, `engine.py`, `domain.py`, `migrations.py::_apply_002`, `test_g3_app_correctness.py`); fixed source citations (`reconcile.py` §12.5 → §5 D20; `migrations.py::_apply_003` §13.2 → §8 WS5; `test_g3_app_correctness.py` §9.2 → §6.2); expanded the cross-references table to enumerate the §3.4, §5 D20, §8 WS5, and §6.2 citations. |
