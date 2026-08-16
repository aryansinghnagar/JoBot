# NOW QUEUE — Active Focus

Current Version: `release-1.0-dev` (JoBot Merge Plan — phased delivery)
Current Status: Phase 3 (Resume + Cover-Letter + Auto-Apply) COMPLETED — 224 passed / 11 skipped, ruff+mypy clean. Next: Phase 4.

## Milestone Trajectory

- [x] **Phase 0**: Pre-flight (canonical docs, baseline, contracts) [COMPLETED]
- [x] **Phase 1**: LLM providers, secrets/config, doctor [COMPLETED — pytest 127/3]
- [x] **Phase 2**: Scraping + discovery + dedup (plan.md §316–325) [COMPLETED — pytest 183/9]
- [x] **Phase 3**: Resume/cover tailoring + auto-apply orchestration (plan.md §327–339) [COMPLETED — pytest 224/11; exit: `jobot apply --dry-run` → PDF + cover + ATS ≥ 0.85]
- [ ] **Phase 4**: Per JoBot Merge Plan (see plan.md §340+) [PENDING]
- [ ] **dev-2.0**: Tauri 2 + React Desktop GUI [PLANNED FOR RELEASE 2.0]

## Phase 3 Exit Notes

- Live LLM degraded on this machine (gemini OAuth 401) — degradation paths verified truthful via grounding gate; live browser runs opt-in (`JOBOT_RUN_LIVE_BROWSER=1`).
- Runner.py deliberately NOT wired to ApplyOrchestrator (LLM tailoring cost per campaign application unjustified); `jobot apply` is the orchestrated path.
