# NOW QUEUE — Active Focus

**Current authority:** `MASTER_PLAN_EXPANDED.md` (2026-08-16). Supersedes `MASTER_PLAN.md` and all Plan1–Plan11 source documents for execution purposes.
**Current status:** WS0+WS1 (`ebf700b`, G1 PASS_LOCAL), WS2 (`a82fc59`, G2 PASS_LOCAL), WS3 (G3 PASS_LOCAL, 613 tests) all committed 2026-08-16. Next: WS4 browser+adapters and WS5 AI reliability (parallelizable per §6 rails). Push to origin to trigger CodeQL rescan + first security-gates run.

## Active Milestone — M1: v1.0.0 per MASTER_PLAN_EXPANDED.md

- [x] **P0 Baseline (WS0 / gate G0):** test/audit/version baselines machine-verified and committed under `docs/quality/production-readiness.md` with 0–10 scorecard (coverage + perf baselines deferred to CI tooling — see improve queue).
- [x] **WS1 (gate G1) — DONE (PASS_LOCAL):** npm audit 0, URL sanitization + adversarial suite, SSRF guard choke point, vault hardening, Tauri CSP + args allowlist, version authority 0.2.0, SHA-pinned CI + security-gates, governance files. Residuals pending push: CodeQL rescan confirmation, pip-audit first CI run, trusted-publishing (owner).
- [x] **WS2 (gate G2) — DONE (PASS_LOCAL):** migrations runner + `jobot db/task/approval` CLI, DurableTaskEngine (atomic leases/heartbeats/quarantine), event ledger, effect idempotency, durable approvals; kill-anywhere proven (artifacts/gates/G2.json).
- [x] **WS3 (gate G3) — DONE 2026-08-16 (PASS_LOCAL):** application state machine (§3.4 + UNKNOWN states + outcome/timestamp stamping), effect ledger wired into ASP phases 10-12 (reserve-before-submit, reconcile-never-replay), durable approval gate on submit_and_verify (CLI/GUI/saga paths decide it), H7 ReconciliationService (verify-only, quarantine after 3 ambiguous attempts), migration v2 timestamp split + backfill (artifacts/gates/G3.json).
- [x] **WS4 (gate G4) — DONE 2026-08-16 (PASS_LOCAL):** BrowserSessionPool (UC-09), selector registry + fallback healing (UC-10), browser evidence protocol with SHA256 DOM/screenshot hashing (UC-11), CAPTCHA boundary (UC-12), site health monitor & `jobot site-health` CLI (UC-13), CXS adapter family (Ashby, Workable, Recruitee, Teamtailor, BambooHR) (UC-15 & UC-16), LinkedIn Easy Apply saga (UC-17).
- [x] **WS5 (gate G5) — DONE 2026-08-16 (PASS_LOCAL):** Real async LLM streaming across 8 providers (UC-18), candidate truth ledger + `CandidateGroundingVerifier` (UC-21), independent rubric reviewer with drafter-reviewer A-F grading & revision loop (UC-22), 4-stage matching ladder (UC-23), resume PDF/text ingestion & `jobot import-resume` CLI (UC-25), answer bank & form field memory persistence + migration v3 (UC-26).
- [ ] **WS6 (gate G6) — NEXT:** Onboarding journey, dashboard, approval inbox, evidence viewer, incident view, a11y baseline.
- [ ] **WS7 (gate G7) — UPCOMING:** Release packaging, clean install, backup/restore, SBOM, release notes.

## Historical trajectory (complete)

- [x] Phases 0–4 (docs/baseline/contracts; providers/secrets/doctor; scraping/discovery/dedup; tailoring/apply orchestration; tracker/digest/scheduler/interview/analytics/outreach/plugins/Docker+CI)
- [x] Release-1.0 hardening (tagged, then tag retracted and re-earned properly)
- [x] dev-2.0: Tauri 2 + React GUI, 22-method sidecar, Workday honest adapter (tagged release-2.0)
- [x] WS1 security workstream (2026-08-16 session): npm audit 0, URL sanitization + 54 adversarial tests, vault hardening, Tauri CSP + args allowlist, version sync 0.2.0, SHA-pinned CI + security-gates job, governance files, `jobot list-sites` command
- [x] WS3 application correctness (2026-08-16 session): G3 contract landed — submits execute exactly once (breaker retry removed), ambiguous submits reconcile without replay, approvals durable across restarts
- [x] WS4 browser & adapters (2026-08-16 session): BrowserSessionPool, self-healing SelectorRegistry, BrowserEvidenceCollector, SiteHealthMonitor, CXS adapters (Ashby, Workable, Recruitee, Teamtailor, BambooHR)
- [x] WS5 AI reliability & truth (2026-08-16 session): Async streaming across 8 LLM providers, CandidateTruthStore, CandidateGroundingVerifier, Drafter-Reviewer loop, 4-stage MatchingLadder, ResumeImporter

## Standing exit notes (still true)

- GUI JS deps live in ROOT `package.json` (single `npm ci` in CI); `gui/package.json` is a thin wrapper.
- Tauri/Rust build local-only; needs MinGW `dlltool` or MSVC `link.exe` before `tauri:dev`/`tauri:build`; `cargo check` never yet run anywhere (MASTER_PLAN UC-48 closes this).
- Live paths stay opt-in (`JOBOT_RUN_LIVE_BROWSER=1`); no fabricated confirmation IDs, ever.
