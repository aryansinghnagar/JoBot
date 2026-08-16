# NOW QUEUE — Active Focus

**Current authority:** `MASTER_PLAN_EXPANDED.md` (2026-08-16). Supersedes `MASTER_PLAN.md` and all Plan1–Plan11 source documents for execution purposes.
**Current status:** WS0+WS1 committed (`ebf700b`, 571 tests, G1 PASS_LOCAL — CodeQL rescan + first remote security-gates run pending push). WS2 committed (593 tests, G2 PASS_LOCAL). WS3 application correctness is next.

## Active Milestone — M1: v1.0.0 per MASTER_PLAN_EXPANDED.md

- [x] **P0 Baseline (WS0 / gate G0):** test/audit/version baselines machine-verified and committed under `docs/quality/production-readiness.md` with 0–10 scorecard (coverage + perf baselines deferred to CI tooling — see improve queue).
- [ ] **WS1 (gate G1):** landed locally 2026-08-16 — final verification: full pytest + vitest + ruff + sync_versions --check green, then commit. Residuals: CodeQL rescan confirmation, pip-audit first CI run, trusted-publishing switch (needs PyPI side), `black` dev-dep removal.
- [x] **WS2 (gate G2) — DONE 2026-08-16 (PASS_LOCAL):** migrations runner + `jobot db` CLI, DurableTaskEngine (atomic leases/heartbeats/quarantine), event ledger, effect idempotency ledger, durable approvals; kill-anywhere/no-double-lease/duplicate-effect-impossible proven (artifacts/gates/G2.json).
- [ ] **WS3 (gate G3) — NEXT:** application state machine (§3.4 protocol), effect ledger wired into 12-phase ASP, policy as universal pre-effect gate, SUBMISSION_UNKNOWN + reconcile harness (H7), timestamp split migration.

## Historical trajectory (complete)

- [x] Phases 0–4 (docs/baseline/contracts; providers/secrets/doctor; scraping/discovery/dedup; tailoring/apply orchestration; tracker/digest/scheduler/interview/analytics/outreach/plugins/Docker+CI)
- [x] Release-1.0 hardening (tagged, then tag retracted and re-earned properly)
- [x] dev-2.0: Tauri 2 + React GUI, 22-method sidecar, Workday honest adapter (tagged release-2.0)
- [x] WS1 security workstream (2026-08-16 session): npm audit 0, URL sanitization + 54 adversarial tests, vault hardening, Tauri CSP + args allowlist, version sync 0.2.0, SHA-pinned CI + security-gates job, governance files, `jobot list-sites` command

## Standing exit notes (still true)

- GUI JS deps live in ROOT `package.json` (single `npm ci` in CI); `gui/package.json` is a thin wrapper.
- Tauri/Rust build local-only; needs MinGW `dlltool` or MSVC `link.exe` before `tauri:dev`/`tauri:build`; `cargo check` never yet run anywhere (MASTER_PLAN UC-48 closes this).
- Live paths stay opt-in (`JOBOT_RUN_LIVE_BROWSER=1`); no fabricated confirmation IDs, ever.
