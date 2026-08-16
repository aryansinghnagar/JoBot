# NEXT QUEUE — Upcoming Tasks

## P0 & P1 Remedial Tasks (JoBot_Refactor_Review_2.md)
- [x] P0.1: Fix missing `Dict` import in `src/jobot/obs/alerts.py`
- [x] P0.2: Fix missing `json` and `datetime` imports in `src/jobot/cli/main.py`
- [x] P0.3: Fix Greenhouse `submit_application` URL-parser bug and explicit HTTP 404/500 `ApplicationStatus.FAILED` error handling
- [x] P0.4: Retract premature `release-1.0` git tag and sync project state documentation
- [x] P0.5: Fix `EvalHarness` directory creation exception handling and verify 100% test collection
- [x] P1.7: Fix `AdapterRegistry` to raise explicit `ValueError` for unregistered portals
- [x] P1.8: Delete duplicate `@app.command("schedule")` decorator in `src/jobot/cli/main.py`
- [x] P1.9: Remove duplicate Flask server fixtures in `test_asp.py` and `test_qa_engine_wired.py`
- [x] P1.10: Delete dead duplicate `CircuitBreaker` in `src/jobot/failure/catalog.py`
- [x] P2.6: Write CLI test suite `tests/test_cli_commands.py`

## Active P1 Adapter Upgrades (In Progress)
- [ ] P1.1: Naukri real `submit_application` driving Patchright browser context
- [ ] P1.2: Naukri real `verify_submission` checking portal application history
- [ ] P1.3: Naukri real `discover_jobs` scraping search results
- [ ] P1.4: Dynamic `SkillExtractor` execution across all adapter job descriptions

## Release 2.0 Roadmap (Planned)
- [ ] T4.1: Tauri 2 + React Desktop GUI Integration
- [ ] T4.2: Workday & Lever Native Adapters
