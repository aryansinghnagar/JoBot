# JoBot Production Readiness Plan

**Version:** 1.0 · 2026-08-15 · Status: APPROVED-PENDING-EXECUTION
**Target release:** `v1.0.0` (production, release & commercial use)
**Companion docs:** [`SETUP.md`](./SETUP.md) · [`docs/contracts.md`](./docs/contracts.md) · [`worklog.md`](./worklog.md) · [`queues/`](./queues/)

## 1. Objective

Take JoBot from Release 2.0 (feature-complete, tagged) to a production-grade,
releaseable, commercially usable open-source product:

- **Pure open source** — AGPL-3.0 core; monetization via sponsorship, not licensing
- **All three distribution channels** — PyPI wheel, Docker images (GHCR), signed desktop installers (Windows/macOS/Linux) with auto-update
- **Single-user local-first scope** — no auth, billing, or hosted SaaS in v1

Definition of done for `v1.0.0`: a tagged release whose artifacts (wheel,
containers, installers) are produced by a reproducible CI pipeline, all gates
green, security posture documented, opt-in telemetry, crash reporting, docs
site live, community governance files in place, and the release announced.

## 2. Verified Baseline (2026-08-15)

| Area | State |
|---|---|
| Tests | pytest 359 passed / 13 skipped (13 = live opt-in); vitest 18/18; prettier clean |
| Static | ruff check/format clean; mypy clean (116 files, strict) |
| CI | 3-OS × 2-Python quality matrix; npm-quality; SBOM + provenance attestation; CodeQL weekly; Dependabot |
| Release | PyPI publish-on-release workflow (token auth); `release-1.0` + `release-2.0` tags pushed |
| Packaging | Multi-stage Dockerfile + compose; Tauri 2 shell (`gui/src-tauri`) |
| Ops built-ins | `jobot backup/migrate/trace/quarantine/doctor/config`; keyring + Fernet secrets; 22-method JSON-RPC sidecar; scheduler + daily caps |
| Adapters | Honest no-fabrication: naukri/linkedin/workday live browser opt-in (`JOBOT_RUN_LIVE_BROWSER=1`), lever/greenhouse/ashby/smartrecruiters real APIs, 8 JobSpy boards |

## 3. Known Gaps (inputs to this plan)

1. Version drift: `pyproject.toml` 0.1.0, root `package.json` 0.1.0, `gui` 2.0.0, `tauri.conf.json` 2.0.0 — no single source of truth
2. No `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT`, issue/PR templates, `FUNDING.yml`
3. `README.md` is 25 lines — no quickstart, badges, screenshots, architecture
4. `npm audit`: 3 vulnerabilities (1 moderate, 2 high) — not gated in CI; no `pip-audit`/osv-scanner
5. Tauri CSP is `null`; capability permissions not re-audited since first draft
6. Placeholder solid-color icons; no desktop CI builds, code signing, or auto-updater
7. `cargo check` never verified (no C toolchain on dev machine; CI has none either)
8. No coverage threshold gate; no failure-injection, soak, or GUI E2E tests
9. No telemetry/crash reporting; no privacy documentation
10. `queues/improve.md` stale — lists 9 subsystems as unwired though worklog shows QAEngine/PolicyEngine/CircuitBreaker/TraceLogger/AlertDispatcher wired in Phase 1
11. LICENSE lacks a copyright holder line; README's "adapters MIT" claim unverified
12. GitHub Actions not pinned to SHAs; no secret scanning in CI
13. Docker images not published; compose not smoke-tested in CI

## 4. Non-Negotiable Rules (inherit from AGENTS.md)

- No fabrication ever: adapters, telemetry claims, and release notes must be honest (opt-in live paths stay opt-in)
- Every phase leaves artifacts: test evidence, docs, changelog entries, worklog rows
- Gates before tags: no release without full gate suite green
- Opt-in telemetry only, with redaction and a kill switch; privacy doc must match code exactly
- File-based state: queues/plan/changelog updated during execution, not only at the end

## 5. Phases & Tasks

### Phase R1 — Foundation & Release Engineering (weeks 1–2)

| ID | Task | Verification |
|---|---|---|
| R1.1 | Version unification: bump `pyproject.toml` to 1.0.0; add `scripts/sync_versions.py` writing root/gui `package.json` + `tauri.conf.json` from pyproject; semver policy in `docs/release-policy.md` | `scripts/sync_versions.py` idempotent; all four files match; CI check job fails on drift |
| R1.2 | `CHANGELOG.md` (Keep a Changelog) backfilled from worklog (Phases 0–6) + `Unreleased` section | Markdown lint passes; entries traceable to worklog rows |
| R1.3 | Coverage gate: `pytest --cov=jobot --cov-fail-under=75` (measure current first; set floor at measured −2% if below) | CI pip-quality job fails below floor; coverage report artifact |
| R1.4 | Security gates: `npm audit --audit-level=high` + `pip-audit` + `gitleaks` scan in CI; resolve the 3 npm vulns (pin/upgrade) | CI jobs green; `npm audit` clean; gitleaks finds 0 on full history |
| R1.5 | Actions hardening: pin all GH actions to commit SHAs; add `permissions: contents: read` everywhere; Dependabot extended to pip+npm with monthly grouping | `actionlint` clean; dependabot PRs open for stale deps |
| R1.6 | Governance files: `SECURITY.md` (reporting + PGP), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, `FUNDING.yml`, `.editorconfig` | Files exist; CONTRIBUTING runbook executes end-to-end (fresh clone → gates green) |
| R1.7 | License hygiene: add copyright holder line to LICENSE; audit headers (AGPL core, MIT adapters — correct claims or simplify README); add `NOTICE` if needed | `reuse lint`-style audit report; README claim matches reality |
| R1.8 | README overhaul: badges (CI/coverage/license/PyPI), quickstart (pip/Docker/desktop), GUI screenshots (placeholder until R2 icons), architecture diagram, FAQ, sponsorship links | README renders; quickstart verified in fresh venv |
| R1.9 | Local gates script: `scripts/gates.ps1` + `scripts/gates.sh` (pytest, ruff, mypy, vitest, prettier, npm audit, sync_versions check) | Scripts exit 0 on clean tree, non-zero on seeded break |
| R1.10 | Momentum queues rewrite: reconcile `queues/improve.md` (mark wired items done), reframe `now/next/blocked` around this plan | Queues match repo truth; no stale claims |

### Phase R2 — Distribution Artifacts (weeks 2–4)

| ID | Task | Verification |
|---|---|---|
| R2.1 | PyPI trusted publishing: switch `publish.yml` to `trusted-publishing` (id-token) + environment `pypi`; version + readme metadata; verify `jobot` console script on 3 OSes | `twine check` clean; publish to TestPyPI in a dry run |
| R2.2 | Docker publishing: GHCR release workflow (amd64+arm64 manifests), `docker compose` smoke test in CI (doctor + scrape mock_ats), tags `1.0.0` + `latest` | Multi-arch image pulls and runs on both platforms; SBOM attached |
| R2.3 | Desktop CI builds: new `desktop.yml` — windows-latest (NSIS + MSI), macos-latest (DMG), ubuntu (AppImage + deb) via `npm run tauri:build`; `cargo check` added as a CI gate job (closes the C-toolchain gap) | Artifacts uploaded on tag; installers launch on clean VMs (smoke: process starts, window title "JoBot Desktop") |
| R2.4 | Real icon set: design/commit an SVG; `npm run tauri icon` generates full suite; replace placeholder | Icons render in CI-built artifacts; bundle metadata (productName, identifier) correct |
| R2.5 | Auto-update: `tauri-plugin-updater` + generated signing keys (committed per Tauri convention), endpoints → GitHub Releases; update manifest per release | Dev machine applies a staged dummy update; updater disabled gracefully without network |
| R2.6 | Code signing (Windows): evaluate SignPath OSS free tier → Authenticode signing in CI; fallback documented | Signed MSI/EXE passes `signtool verify`; if deferred, README/SETUP documents the SmartScreen caveat |
| R2.7 | Code signing (macOS): decision gate — Apple Developer ($99/yr) notarization vs defer. If defer: document Gatekeeper workaround (right-click open, `xattr -dr com.apple.quarantine`) | Decision recorded in `decisions.md`; release notes state signing status honestly |
| R2.8 | CSP hardening: replace `"csp": null` with restrictive default (script-src self, style-src self+unsafe-inline, connect-src self); re-audit `capabilities/default.json`; verify GUI works under CSP in dev+build | `tauri:dev` + `tauri:build` run clean; no console CSP violations |
| R2.9 | Release pipeline assembly: single `release.yml` orchestrating R2.1–R2.3, attaching SBOMs + provenance attestation (extend existing supply-chain job to artifacts) | One tag produces wheel + images + installers + SBOMs; provenance attestations verifiable via `gh attestation verify` |

### Phase R3 — Reliability Hardening (weeks 4–6)

| ID | Task | Verification |
|---|---|---|
| R3.1 | Sidecar supervision: GUI auto-respawn on sidecar crash/exit; EOF and stdin backpressure handling; Windows process-tree kill on GUI exit; pid-file/lock against double-run | Unit tests (fake process lifecycle) + manual kill test in `tauri:dev` |
| R3.2 | Failure injection suite: adapter timeouts, HTTP 500/429, malformed JSON, browser-crash, sidecar killed mid-RPC — assert circuit breaker opens, quarantine receives work, GUI surfaces recovery | New `tests/test_failure_injection.py` green; no silent failures |
| R3.3 | Soak tests: 1,000-iteration sidecar loop (memory leak check via `tracemalloc`, SQLite WAL growth, `PRAGMA wal_checkpoint` behavior); GUI long-session stability script | Soak report: RSS bounded (±10%), DB growth linear, 0 crashes; artifacts saved |
| R3.4 | Backup/restore hardening: encrypted `jobot backup` round-trip with golden DB fixtures, corruption detection, scheduled backup doc; restore exercised in CI | CI restore test passes from fixtures; backup includes GUI/telemetry state where applicable |
| R3.5 | Observability: structured JSONL logs + rotation config; AlertDispatcher wired (email/webhook on incidents); `jobot trace export` verified end-to-end with real pipeline run | Log format documented; alert fires on seeded incident; exported trace opens in trace viewer |
| R3.6 | GUI E2E: `tauri-driver` + WebDriver tests (boot, discover via mock_ats, apply dry-run, approve, dashboard render) against a real `jobot sidecar` | E2E suite green in CI on windows/ubuntu; screenshots captured as evidence |
| R3.7 | Scheduler robustness: DST/missed-run/catch-up policy tests; daily caps (exists) + quarantine dead-letter verified with adversarial scenarios | New scheduler edge-case tests green |

### Phase R4 — Telemetry & Privacy (weeks 6–7, opt-in only)

| ID | Task | Verification |
|---|---|---|
| R4.1 | Crash reporting: opt-in Sentry SDK (Python core + JS/Rust shell), redaction layer (profile identity, API keys, company/job URLs, evidence paths), consent in GUI onboarding + `jobot config set telemetry.enabled true|false`, `JOBOT_TELEMETRY=off` kill switch | Redaction unit tests (keys/PII never leave process); end-to-end test report with scrubbed payload |
| R4.2 | Anonymous usage analytics: task counts, success/failure rates, cost per run, version — no application data; opt-in same switch | Payload schema documented; test asserts no PII fields; privacy doc matches code |
| R4.3 | `docs/privacy.md`: exactly what is collected, when, how to disable, retention (30 days, no raw payload storage) | Doc reviewed against R4.1/R4.2 code; test enforces schema match |
| R4.4 | Data hygiene: `jobot purge` command (delete applications/evidence/logs per flags), retention defaults, evidence cleanup on uninstall path | Purge tests green; docs updated |
| R4.5 | Health report: `jobot doctor` gains version/env/degradation flags machine-readable (`--json`) for support triage | `doctor --json` schema documented + tested |

### Phase R5 — Docs, Community & Launch (weeks 7–8)

| ID | Task | Verification |
|---|---|---|
| R5.1 | Docs site: VitePress (matches React/Node stack) — setup, CLI reference (from SETUP.md §8), GUI guide, adapters, security, telemetry, FAQ; CI builds site, publishes to GitHub Pages | Site builds clean; links checked; published at docs URL |
| R5.2 | Maintainer runbook: local gates (R1.9), release process checklist (R2.9), branch/tag policy, hotfix path | Runbook executed in a dry-run release; steps all work from fresh clone |
| R5.3 | Community ops: stale-bot, label taxonomy, issue triage automation, public roadmap page (from queues/now.md) | Bot config live; roadmap page renders from queues |
| R5.4 | Launch: tag `v1.0.0` → release pipeline → changelog finalize → announcement (GitHub release + sponsorship call); live-adapter status honestly documented in release notes (opt-in, unvalidated on dev machine) | Release published; artifacts verified downloadable; announcement posted |
| R5.5 | Post-launch backlog: rewrite momentum queues into post-1.0 roadmap (docs site content expansion, localization defer, multi-machine coordination, SaaS exploration notes) | Queues updated; next milestone defined |

## 6. Key Decisions Log

| # | Decision | Default | Owner |
|---|---|---|---|
| D1 | macOS notarization: pay $99/yr vs defer | Defer for v1; document Gatekeeper caveat | maintainer |
| D2 | Windows signing: SignPath OSS tier vs Azure Trusted Signing vs defer | SignPath OSS tier; fallback = defer + documented SmartScreen caveat | maintainer |
| D3 | Auto-update hosting | GitHub Releases (no custom server at OSS scale) | maintainer |
| D4 | Docs site generator | VitePress (existing Node stack) | maintainer |
| D5 | Coverage floor | Measured current −2%, min 70% | maintainer |
| D6 | Sentry vs self-hosted error intake | Sentry SaaS (free tier) for v1 | maintainer |

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| npm audit high vulns unresolvable without breaking Tauri | Release blocked | Investigate first week; pin known-good versions; document residual risk if unavoidable |
| Desktop CI build time/size (Tauri + Rust on 3 OSes) | Slow pipelines, flaky | Separate `desktop.yml` on tag + nightly; cache `~/.cargo` + `target`; time budget ≤ 25 min/job |
| Apple notarization deferred → poor first-run UX on macOS | Adoption friction | Honest release notes + SETUP workaround; re-evaluate at 1.0.1 |
| Live adapters unvalidated (no browser/LLM on dev machine) | False confidence | Keep opt-in; release notes state status; add live validation checklist as follow-up milestone |
| Telemetry redaction regression leaks PII | Trust/legal | Dedicated redaction tests + payload schema test; kill switch tested |
| SQLite single-user ceiling hit by power users | Scope creep | Documented limit; migration path to Postgres noted in roadmap, not built |

## 8. Success Metrics (post-launch, tracked in queues)

- `v1.0.0` artifacts downloadable from all three channels; install-to-doctor ≤ 5 min on each OS
- CI green on every PR; coverage ≥ floor; audit jobs clean
- Telemetry opt-in rate ≥ 10% with zero PII incidents
- First 30 days: ≥ 1 external contribution (issue/PR), sponsorship page live

## 9. Execution Order

R1 (foundation) → R2 (artifacts) → R3 (reliability) → R4 (telemetry) → R5 (launch).
Each phase ends with gates green + worklog/queues/changelog updated. D1–D6 decisions
must be made before their dependent phase starts (D2/D3 before R2.5–R2.7; D1 before R2.7; D4 before R5.1; D5/D6 before R1.3/R4.1).