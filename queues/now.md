# NOW QUEUE — Active Focus

Current Version: `release-1.0-dev` (JoBot Merge Plan — phased delivery)
Current Status: Phase 4 COMPLETED (WS1–WS7 — 289/11). Phase 5: T4.1, P1.1/P1.2, T4.2 done — 318 passed / 13 skipped, ruff+mypy clean. Next: release gates (docs sync, doctor, tag release-1.0).

## Milestone Trajectory

- [x] **Phase 0**: Pre-flight (canonical docs, baseline, contracts) [COMPLETED]
- [x] **Phase 1**: LLM providers, secrets/config, doctor [COMPLETED — pytest 127/3]
- [x] **Phase 2**: Scraping + discovery + dedup (plan.md §316–325) [COMPLETED — pytest 183/9]
- [x] **Phase 3**: Resume/cover tailoring + auto-apply orchestration (plan.md §327–339) [COMPLETED — pytest 224/11; exit: `jobot apply --dry-run` → PDF + cover + ATS ≥ 0.85]
- [x] **Phase 4 WS1**: Tracker analytics + dashboard HTML + responded_at/outcome (plan.md §341) [COMPLETED — `jobot tracker dashboard-html`]
- [x] **Phase 4 WS2**: Weekly digest + SMTP email + 4-mode scheduler loop (plan.md §345-348) [COMPLETED — `jobot digest`, `jobot loop`; pytest 245/11]
- [x] **Phase 4 WS3+**: InterviewPrep, CareerAnalytics, Outreach, plugins, Docker+CI (plan.md §342-344, 349-353) [COMPLETED — `jobot interview/skill-gap/salary/outreach/plugin`; pytest 289/11; committed 38cc024]
- [ ] **Phase 5**: Release-1.0 hardening [IN PROGRESS — T4.1, P1.1/P1.2, T4.2 done; release gates next]
- [ ] **dev-2.0**: Tauri 2 + React Desktop GUI [PLANNED FOR RELEASE 2.0]

## Phase 3 Exit Notes

- Live LLM degraded on this machine (gemini OAuth 401) — degradation paths verified truthful via grounding gate; live browser runs opt-in (`JOBOT_RUN_LIVE_BROWSER=1`).
- Runner.py deliberately NOT wired to ApplyOrchestrator (LLM tailoring cost per campaign application unjustified); `jobot apply` is the orchestrated path.
