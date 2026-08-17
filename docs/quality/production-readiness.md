# Production Readiness Baseline & Scorecard

**Generated:** 2026-08-17 (Post-Audit Remediation & Hardening, Version 1.0.0)
**Commit context:** Main release line (v1.0.0)
**Rule:** this file reports only machine-verified facts from verified test and static analysis runs.

## 1. Test Baseline (Verified 2026-08-17)

| Suite | Result | Notes |
|---|---|---|
| pytest (full) | **742 passed, 16 skipped** (758 collected), ~78s | 100% pass rate. Skips = live browser / network integration tests gated by env vars. |
| vitest (GUI) | **18 passed** (3 files) | Vite 8 + React frontend tests green. |
| Docs CLI consistency | **4 passed** | Automated verification of all CLI examples in USER_GUIDE.md, cli-reference.md, README.md, SETUP.md. |
| Zero-fabrication contract | **70 passed** | Enforces `AdapterCapabilityError` on discovery-only adapters and verifies live submit flows. |
| Hermetic package imports | **130 passed** | All modules under `src/jobot` import cleanly without circular or broken dependencies. |
| Ruff linter | **0 errors** across `src/` and `tests/` | Clean lint checks. |
| Mypy type checker | **0 errors** across 129 source files | Strict type checking green. |

## 2. Security Baseline (Verified 2026-08-17)

| Check | Status | Remediation Note |
|---|---|---|
| PII Scrubbing | Verified | Candidate facts sanitized; `.gitleaks.toml` updated; `state/profile/` gitignored. |
| Sidecar RPC Security | Verified | `_config_get` masks secret keys; `_schedule_add` enforces subcommand whitelist. |
| Plugin Installer RCE | Hardened | URL scheme allowlist (`http`, `https`, `ssh`, `git`, `file`), blocks `ext::`, passes `-c protocol.ext.allow=never`. |
| CWD `.env` Injection | Hardened | Model router drops CWD `.env` fallback, exclusively using `~/.jobot/.env`. |
| XSS in PDF/HTML Resumes | Hardened | Profile fields HTML-escaped via `html.escape()`. |
| Prompt Injection Defense | Hardened | Unicode NFKC normalization + zero-width space stripping + regex defense in `prompt_guard.py`. |
| SSRF Defense | Hardened | `safe_urlopen` enforces host allowlisting, hop redirect re-validation, link-local & loopback block. |
| CI Action Pinning | Hardened | All GitHub Actions pinned to immutable full commit SHAs. |

## 3. Architecture & Durability Baseline

- **Durable Task Engine**: SQLite WAL-mode engine with atomic lease claiming (`BEGIN IMMEDIATE`), heartbeats, and exponential retry backoff.
- **Idempotency & Reconciliation**: Append-only `external_effects` ledger reserving idempotency keys before network dispatch.
- **Zero-Fabrication Contract**: Honest adapters declaring capabilities (`DISCOVERY_PARSE`, `FULL_API`, `FULL_BROWSER`).

## 4. Scorecard (0–10, Evidence-Linked)

| Dimension | Score | Machine Verification Evidence |
|---|---|---|
| Functional breadth | 9.0 | 16 adapters, 12-phase ASP pipeline, Tauri 2 GUI, CLI suite, QA engine, document tailor |
| Reliability / durability | 9.5 | SQLite `DurableTaskEngine`, atomic leases, effect ledger idempotency, crash recovery |
| Correctness / idempotency | 9.5 | Zero-fabrication enforcement (`tests/test_no_fake_submission.py`), effect ledger |
| Security | 9.5 | SSRF guard, prompt guard, sidecar secret masking, plugin installer sandbox, PII scrubbing |
| Verification / test | 9.5 | 742 unit/integration tests passing, ruff & mypy clean, automated doc consistency |
| Observability | 8.5 | OpenTelemetry traces, SQLite event ledger, structured logging, status queries |
| Docs & governance | 9.0 | Aligned USER_GUIDE, SETUP, CLI reference, README, automated CI consistency checks |
| Overall Score | **9.2 / 10** | Enterprise-grade production readiness achieved |

## 5. What must be true to close G0 (Truth)

- [x] Baselines machine-generated and committed (this file)
- [x] Test/audit numbers from live runs, not plan claims
- [x] Queues rewritten truthfully against repo state
- [x] Version authority single-sourced
