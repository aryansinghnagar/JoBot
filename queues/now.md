# NOW QUEUE — Active Focus

Current Version: `release-1.0-dev` (JoBot Merge Plan — phased delivery)
Current Status: Phase 4 (ATS/Analytics/Plugins/Docker) — WS1 Tracker + WS2 Digest/Email/4-mode Loop COMPLETED — 245 passed / 11 skipped, ruff+mypy clean. Next: WS3+.

## Milestone Trajectory

- [x] **Phase 0**: Pre-flight (canonical docs, baseline, contracts) [COMPLETED]
- [x] **Phase 1**: LLM providers, secrets/config, doctor [COMPLETED — pytest 127/3]
- [x] **Phase 2**: Scraping + discovery + dedup (plan.md §316–325) [COMPLETED — pytest 183/9]
- [x] **Phase 3**: Resume/cover tailoring + auto-apply orchestration (plan.md §327–339) [COMPLETED — pytest 224/11; exit: `jobot apply --dry-run` → PDF + cover + ATS ≥ 0.85]
- [x] **Phase 4 WS1**: Tracker analytics + dashboard HTML + responded_at/outcome (plan.md §341) [COMPLETED — `jobot tracker dashboard-html`]
- [x] **Phase 4 WS2**: Weekly digest + SMTP email + 4-mode scheduler loop (plan.md §345-348) [COMPLETED — `jobot digest`, `jobot loop`; pytest 245/11]
- [ ] **Phase 4 WS3+**: InterviewPrep, CareerAnalytics, Outreach, plugins, Docker [PENDING]
- [ ] **dev-2.0**: Tauri 2 + React Desktop GUI [PLANNED FOR RELEASE 2.0]

## Phase 3 Exit Notes

- Live LLM degraded on this machine (gemini OAuth 401) — degradation paths verified truthful via grounding gate; live browser runs opt-in (`JOBOT_RUN_LIVE_BROWSER=1`).
- Runner.py deliberately NOT wired to ApplyOrchestrator (LLM tailoring cost per campaign application unjustified); `jobot apply` is the orchestrated path.
