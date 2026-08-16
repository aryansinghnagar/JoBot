# NOW QUEUE — Active Focus

Current Version: `release-2.0-dev` (JoBot Merge Plan — phased delivery)
Current Status: Release 2.0 COMPLETE (Workday honest adapter + Tauri 2/React GUI + sidecar JSON-RPC) — 359 passed / 13 skipped, ruff+mypy clean, vitest 18/18, prettier clean, tagged release-2.0.

## Milestone Trajectory

- [x] **Phase 0**: Pre-flight (canonical docs, baseline, contracts) [COMPLETED]
- [x] **Phase 1**: LLM providers, secrets/config, doctor [COMPLETED — pytest 127/3]
- [x] **Phase 2**: Scraping + discovery + dedup (plan.md §316–325) [COMPLETED — pytest 183/9]
- [x] **Phase 3**: Resume/cover tailoring + auto-apply orchestration (plan.md §327–339) [COMPLETED — pytest 224/11; exit: `jobot apply --dry-run` → PDF + cover + ATS ≥ 0.85]
- [x] **Phase 4 WS1**: Tracker analytics + dashboard HTML + responded_at/outcome (plan.md §341) [COMPLETED — `jobot tracker dashboard-html`]
- [x] **Phase 4 WS2**: Weekly digest + SMTP email + 4-mode scheduler loop (plan.md §345-348) [COMPLETED — `jobot digest`, `jobot loop`; pytest 245/11]
- [x] **Phase 4 WS3+**: InterviewPrep, CareerAnalytics, Outreach, plugins, Docker+CI (plan.md §342-344, 349-353) [COMPLETED — `jobot interview/skill-gap/salary/outreach/plugin`; pytest 289/11; committed 38cc024]
- [x] **Phase 5**: Release-1.0 hardening [COMPLETED — T4.1, P1.1/P1.2, T4.2, release gates; tagged release-1.0]
- [x] **dev-2.0**: Tauri 2 + React Desktop GUI + Workday honest adapter [COMPLETED — sidecar JSON-RPC, 5 React views, Tauri 2 shell, vitest 18/18; tagged release-2.0]

## Release 2.0 Exit Notes

- GUI JS deps live in the ROOT `package.json` (CI runs a single `npm ci`); `gui/package.json` is a thin wrapper.
- Tauri/Rust build is local-only (not in CI gates). `cargo check` on this machine needs a Windows C toolchain (MinGW `dlltool` or MSVC `link.exe`) — install one before `npm run tauri:dev` / `tauri:build`.
- Workday adapter is honest: cxs JSON API for discovery/parse, Patchright submit/verify gated on `JOBOT_RUN_LIVE_BROWSER=1`, no fabricated confirmation IDs.
- Sidecar is the single GUI↔backend bridge: `jobot sidecar` (22 JSON-RPC methods); doctor logic shared via `src/jobot/doctor.py`.

## Phase 3 Exit Notes

- Live LLM degraded on this machine (gemini OAuth 401) — degradation paths verified truthful via grounding gate; live browser runs opt-in (`JOBOT_RUN_LIVE_BROWSER=1`).
- Runner.py deliberately NOT wired to ApplyOrchestrator (LLM tailoring cost per campaign application unjustified); `jobot apply` is the orchestrated path.
