# Changelog

All notable changes to JoBot are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
JoBot has **not shipped a stable release**: the package version in
`pyproject.toml` is `0.2.0` (unified across all manifests 2026-08-16), and no
versioned distribution has been published. The version headings below are
**development milestones** matching git tags on `main`, not stable releases.
Semantic Versioning will be adopted once a 1.0.0 release exists.

## [Unreleased]

### Added

- **Audit remediation — 2026-08-19.** Reconstructed `MASTER_PLAN_EXPANDED.md`
  (was referenced 40+ times across governance docs and 8 source modules but
  absent from the repository — audit finding JOB-OSS-004). The new document
  contains the decision register (D1–D24), risk register (R1–R17),
  verification doctrine (L1–L9, G0–G7), and production-readiness workstreams
  (WS0–WS8) that every previously-dangling citation now resolves to.
- **Audit remediation — 2026-08-19.** Added `AUDIT_REMEDIATION.md` at the
  repo root, documenting each fix applied in response to the deep forensic
  audit. Each entry cross-references the finding ID (JOB-*), the file
  touched, and the rationale.
- **WS3 — application correctness (gate G3).** Application protocol state
  machine (`jobot.applications.state_machine`, §3.4 transition table with
  first-class SUBMISSION_UNKNOWN / VERIFICATION_UNKNOWN / outcome states and
  split-timestamp stamping); the 12-phase pipeline reserves an effect in the
  idempotency ledger BEFORE submitting and maps post-send failures to
  SUBMISSION_UNKNOWN (reconcile, never retry); durable approvals gate
  `submit_and_verify` across restarts; H7 `ReconciliationService` is
  structurally submit-free and quarantines after 3 ambiguous verification
  attempts; migration v2 splits application timestamps with legacy backfill.
- Expanded master plan (`MASTER_PLAN_EXPANDED.md`): gap matrix, decision
  register (D1-D24), verification doctrine (L1-L9, G0-G7), risk register, and
  a production-readiness workstream track (WS1-W8+).
- Governance file set: `SECURITY.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, this changelog, `.github/FUNDING.yml`,
  `.github/CODEOWNERS`, issue templates, pull request template, and
  `.editorconfig`.
- Production-readiness baseline & scorecard
  (`docs/quality/production-readiness.md`) with machine-verified test/audit
  numbers (WS0, gate G0).
- `jobot list-sites` CLI command plus friendly `--site` guidance when a
  URL's site cannot be inferred (decision D1).
- Adversarial URL-sanitization suite `tests/test_url_inference.py` (54
  cases) and vault-hardening suite `tests/test_vault_hardening.py`.
- Undeclared-dependency import guard `tests/test_imports.py` (117 module
  checks against the `pyproject.toml` dependency universe).
- CI security-gates workflow: pip-audit (`--strict`), npm audit
  (`--audit-level=high`), gitleaks full-history scan via `.gitleaks.toml`.
- Version-authority script `scripts/sync_versions.py` with `--check` drift
  mode (canonical source: `pyproject.toml`).

### Changed

- **Audit remediation — 2026-08-19.** Version authority reconciled: all
  five manifests (`pyproject.toml`, `package.json`, `gui/package.json`,
  `gui/src-tauri/tauri.conf.json`, `gui/src-tauri/Cargo.toml`) now declare
  `0.2.0`, matching `SECURITY.md`, this changelog, and `CONTRIBUTING.md`.
  `jobot.__version__` and the sidecar `_ping` RPC handler now read the
  canonical version from `jobot.updater.get_current_version()` instead of a
  hardcoded string. CI runs `python scripts/sync_versions.py --check` on
  every supply-chain job to prevent future drift (fixes JOB-ARC-010).
- **Audit remediation — 2026-08-19.** `continuous-campaign` CLI default
  flipped from `--auto-submit` to `--supervised` (fixes JOB-SEC-001 /
  JOB-UX-005 / JOB-ARC-003). The CLI now prints an explicit ToS-risk
  warning and requires interactive `y/N` confirmation before starting any
  campaign; autonomous mode requires a second confirmation. The runner's
  inter-iteration sleep was raised from `0.05s` to a randomized `5–15s`
  window to respect portal rate-limit courtesy.
- **Audit remediation — 2026-08-19.** All four HTTP-based LLM providers
  (`OpenAIProvider`, `AnthropicProvider`, `MistralProvider`,
  `CohereProvider`) now call `http_post_json_async` (which delegates to
  `asyncio.to_thread(http_post_json, ...)`) instead of the synchronous
  `http_post_json`. The event loop is no longer frozen for the full LLM
  call window — fixes JOB-ARC-005 / JOB-ARC-004. The synchronous helper is
  retained for non-async call sites.
- **Audit remediation — 2026-08-19.** Plugin installer no longer accepts
  the `file://` scheme by default (fixes JOB-SEC-003). Local-path plugin
  installs are gated behind the `JOBOT_ALLOW_LOCAL_PLUGIN_INSTALL=1` env
  var, which is intended for the test suite only. Bare local paths and
  Windows drive-letter paths are refused with a clear error message.
- **Audit remediation — 2026-08-19.** Plugin import scanner rewritten to
  use the Python AST instead of substring matching (fixes JOB-SEC-013).
  The previous substring scan was bypassable via `__import__("subprocess")`,
  string concatenation, or `getattr(module, "system")(...)`. The new AST
  walker inspects `Import`, `ImportFrom`, and `Call` nodes for forbidden
  modules and dynamic code-execution globals (`__import__`, `eval`, `exec`,
  `compile`).
- **Audit remediation — 2026-08-19.** Untrusted ATS questions are now
  wrapped in `<UNTRUSTED_INPUT>...</UNTRUSTED_INPUT>` delimiters before
  being interpolated into the QA-engine LLM prompt (fixes JOB-ARC-007).
  A system message instructs the model to treat the delimited content as
  data, not as instructions. This is defense in depth on top of the
  existing regex-based `sanitize_llm_input` scrubber.
- **Audit remediation — 2026-08-19.** Removed `--no-sandbox` from the
  Patchright/Chromium launch args (fixes JOB-SEC-012). The sandbox is the
  boundary that limits a malicious page's blast radius; disabling it
  turns every renderer compromise into a full-process compromise. Docker
  users should configure the container with `--cap-add=SYS_ADMIN` instead
  of disabling the sandbox globally. `--disable-dev-shm-usage` is kept
  (benign Docker workaround).
- **Audit remediation — 2026-08-19.** Ruff lint rules expanded from
  `E,F,W` to include `S` (bandit security), `B` (bugbear), `C90`
  (mccabe complexity), `UP` (pyupgrade), and `I` (isort) (fixes
  JOB-SEC-006). Per-file ignores are configured for the test suite (which
  legitimately uses `assert`, hardcoded test secrets, and `/tmp` paths).
- **Audit remediation — 2026-08-19.** Dependency lower bounds raised to
  versions that fix known CVEs (fixes JOB-SEC-019): `cryptography>=42.0.4`
  (was `>=41.0.0`, which admitted CVE-2023-50782 / CVE-2024-26130),
  `jinja2>=3.1.3` (was `>=3.1.0`, which admitted CVE-2024-22195),
  `pyyaml>=6.0.2` (was `>=6.0`, which admitted CVE-2024-49770).
- **Audit remediation — 2026-08-19.** Cover-letter generator now guards
  against the `[LLM_UNAVAILABLE]` degradation sentinel (fixes
  JOB-SEC-020). Previously the literal string
  `[LLM_UNAVAILABLE] Information from profile facts: ...` could flow into
  the cover-letter PDF and be submitted to the employer. The generator now
  returns an empty letter and logs a warning when the sentinel is
  detected.
- `AGENTS.md` operating doctrine updated to match the expanded plan.
- **Behavioral (G3 contract):** an adapter exception during submission now
  leaves the application SUBMISSION_UNKNOWN (was FAILED) and the effect
  UNKNOWN — reconciliation verifies, it never re-submits; re-running the
  pipeline on the same job after an ambiguous or committed submission
  returns DUPLICATE_SKIPPED; submissions execute exactly once through the
  circuit breaker (outcome recorded, retry removed — the retry could
  double-submit after a post-send failure).
- **Security: URL inference is exact, not substring.** `infer_site()` now
  matches parsed hostnames against site suffixes and raises `ValueError` for
  unknown hosts instead of silently defaulting to the greenhouse adapter;
  `WorkdayApi._split_company()` applies the same host-suffix rule. Fixes the
  root cause of 9 CodeQL `py/incomplete-url-substring-sanitization` alerts
  (alert closure pending platform rescan).
- **Security: vault keyfile hardening.** The master-key fallback file is
  created atomically with 0600 permissions (`O_EXCL` + `os.replace`), read
  with `O_NOFOLLOW`, and refused fail-closed when its mode was loosened
  (POSIX); encrypted profile writes are atomic with no partial-write window.
- **Security: Tauri shell narrowed.** CSP is set (was `null`) and the shell
  plugin accepts exactly one argument pattern (`^sidecar$`) instead of
  arbitrary args.
- **Dependencies: npm stack upgraded.** vite 8.2.1, vitest 4.1.10,
  `@vitejs/plugin-react` 6.0.5, `@tauri-apps/*` 2.11.x, `engines.node
  >= 20.19`; `npm audit` now reports 0 vulnerabilities (was 3, incl. 2 high).
- **Security: SSRF guard on every outbound fetch.** New
  `jobot.security.url_guard` choke point (http/https only, no embedded
  credentials, literal private/loopback/link-local hosts refused, resolved
  loopback/link-local answers refused — cloud-metadata range included,
  NAT64/DNS64 networks deliberately not penalized), `safe_urlopen` fetcher
  with per-hop redirect re-validation, wired into all adapters, scrapers,
  the stealth HTTP client, LLM REST helpers, and salary live fetch;
  `tests/test_url_guard.py` (37 cases).
- **Security: SQL migrations are literal statements.** `storage/db.py`
  additive migrations now execute fixed SQL strings at the call site
  (no identifier interpolation).
- **Security: alert store writes are atomic and traversal-free.**
  `obs/alerts.py` rejects `..` path components at construction and rewrites
  via temp-file + `os.replace`.
- All CI actions SHA-pinned (20/20 references across 4 workflows); node
  matrix 20/22; ruff no longer narrowed to `--select E,F`.
- Versions unified at 0.2.0 across `pyproject.toml`, both `package.json`
  manifests, and `tauri.conf.json` (was drifting 0.1.0 / 2.0.0).
- Repo-wide lint debt cleared: 21 pre-existing unused imports removed; CI
  ruff gate runs without `--ignore F401`; unused `black` CI dependency
  dropped.

## [release-2.0] - 2026-08-15

Development milestone: desktop GUI era. Python core plus a Tauri 2 shell.

### Added

- **Desktop GUI**: Tauri 2 + React 18 shell in `gui/` with five views
  (dashboard, discovery, applications/approvals, tracker, diagnostics) that
  talk to the backend exclusively through the sidecar; the Rust shell is
  intentionally thin (it only spawns the sidecar process) and shows a
  sidecar-unavailable message instead of crashing.
- **Full JSON-RPC sidecar surface** (`jobot sidecar`,
  `src/jobot/gui/sidecar.py`): 22 line-delimited JSON-RPC 2.0 methods over
  stdio — ping, status, profile_info, list_sites, discover_jobs, apply,
  approve, applications, tracker_stats, campaign_status, pause, resume,
  schedule_list/add/remove, digest, doctor, config_show/get/set/unset, and
  traces — with a doctor module shared between CLI and GUI.
- **Workday honest adapter**: discovery and parsing via the Workday `cxs`
  REST API; submit/verify via live browser, opt-in behind
  `JOBOT_RUN_LIVE_BROWSER=1`, with honest no-op reporting when the flag is
  unset.
- GUI test suite under `gui/tests` and `tests/npm`, wired into the existing
  vitest + prettier CI gates.

### Changed

- Documentation synced with the GUI era (SETUP.md Section 7 desktop-GUI
  chapter, contracts addendum).

## [release-1.0] - 2026-08-15

Development milestone: merge-plan execution, Phases 0-5 complete (318 tests
passed / 13 skipped with live tests opt-in; ruff and mypy clean, per the tag
annotation).

### Added

- **Phase 0 — audit and cleanup**: canonical merge-plan docs at repo root,
  superseded plans moved to `docs/history/`, `docs/asp.md` as the 12-phase
  Application Submission Pipeline source of truth, `docs/contracts.md`
  interface freeze, runtime artifacts excluded from version control.
- **Phase 1 — provider abstraction**: cost-aware `ModelRouter` v2 with a
  12-entry provider registry and persisted spend tracking, profiles YAML
  layer, OS-keyring secrets wrapper, `jobot config` and `jobot doctor` CLI.
- **Phase 2 — scrapers and discovery**: `jobot/scrapers/` package (jobspy,
  ATS families, careers pages, dedup), `[scrapers]` optional dependency
  extra, `jobot scrape` / `jobot dedup` CLI, storage-level dedup cache, and
  a discovery-engine rewrite onto real feeds only (never fabricated) with a
  uniform scraper protocol; scraper/dedup/discovery test suite with
  live-scrape tests opt-in via `JOBOT_RUN_LIVE_SCRAPE=1`.
- **Phase 3 — documents and honest adapters**: document stack with LaTeX +
  fallback PDF engines and ATS scorer, resume tailor loop with a
  truthfulness grounding gate, cover-letter tones, real adapters where APIs
  allow it (Lever API, Greenhouse attach, LinkedIn without fabrication),
  LinkedIn Easy Apply browser saga exercised against a hermetic Flask ATS
  harness, ASP saga/orchestrator with `extra_form_data` pipeline, and CLI
  actions (`apply`, `coverletter`, `qa`, `resume`, `scrape --save`, doctor
  engine checks).
- **Phase 4 — workstreams WS1-WS7**: application tracker with analytics and
  HTML dashboard, weekly digest with SMTP email sender, four-mode scheduler
  loop, interview prep, career analytics, outreach presets, plugin system
  (manifest allowlists + static install-time audit), Docker image and CI
  pipelines.
- **Phase 5 — live submission paths**: runner rewired to `ApplyOrchestrator`
  with an LLM cost gate, Naukri real submit/verify via Patchright (no
  fabrication, live opt-in), LinkedIn Easy Apply saga wired into the adapter
  (live opt-in).

## [0.1.0] - 2026-07-22 to 2026-08-06

Initial development era: Python core engine. Internal milestones
`release-1.0-alpha` (mid-refactor snapshot, 2026-07-22) and the "Release 1.0"
refactor completion (2026-07-23) fall inside this period. No distribution was
published; `pyproject.toml` stayed at `0.1.0`.

### Added

- Repository architecture and baseline documentation.
- Core engine: 12-phase Application Submission Pipeline with
  definition-of-done gates, runner, policy engine, QA engine, circuit
  breaker with retry/backoff, trace logger, alert dispatcher, eval harness,
  and 15 site adapters behind a unified `AdapterRegistry`.
- Provider layer: Gemini default with OpenAI, Anthropic, and Ollama
  fallbacks.
- Continuous campaign runner with round-robin portal distribution, daily
  portal caps, `jobot reset-db`, and an auto-submit mode.
- ATS resume compiler, stdio JSON-RPC sidecar server (predecessor of the
  Release 2.0 sidecar surface).
- Mock ATS adapter served by a local Flask server for integration tests;
  test-state isolation via a reset route.
- Dual-stack (npm + pip) CI: ruff lint/format, mypy, pytest, prettier,
  vitest across Linux/Windows/macOS; Dependabot and CodeQL enabled, with
  workflow permissions hardened to `contents: read`.

### Changed

- Project identity standardized to "JoBot" across modules and tests.
- Database writes moved from `INSERT OR REPLACE` to explicit duplicate-error
  handling; hardcoded default-profile identity fallbacks removed.

### Fixed

- `CredentialVault` directory-creation bug, behavioral-mimicry cubic Bezier
  math, eval-harness hardcoded `sc_passed=True`, idempotency key for
  `intent_app`, P0/P1 findings from the first refactor review, and vitest
  upgraded to `^3.2.6` to patch CVE-2026-47429.

[Unreleased]: https://github.com/aryansinghnagar/JoBot/compare/release-2.0...HEAD
[release-2.0]: https://github.com/aryansinghnagar/JoBot/compare/release-1.0...release-2.0
[release-1.0]: https://github.com/aryansinghnagar/JoBot/tree/release-1.0
[0.1.0]: https://github.com/aryansinghnagar/JoBot/tree/release-1.0-alpha
