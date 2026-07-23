# BLOCKED QUEUE — Active Impediments

All active blockers diagnosed in `JoBot_Refactor_Plan.md` have been fully resolved in Release 1.0:

1. **[RESOLVED] Symptom 1: Fake Companies in Log** — Replaced stub adapters with real HTTP API adapters (`GreenhouseAdapter`), Patchright browser automation (`NaukriAdapter`), and Flask Mock ATS integration test suite (`MockATSAdapter`).
2. **[RESOLVED] Symptom 2: Hardcoded Job Titles** — `parse_job_posting` extracts real job title, company, location, and description from URL/API/DOM endpoints.
3. **[RESOLVED] Symptom 3: Hardcoded Skill Match Scores** — Integrated `SkillExtractor` combining LLM prompt extraction and regex keyword matching to evaluate real candidate match scores.
4. **[RESOLVED] Symptom 4: Infinite Loop Runner Without Dedup** — Added explicit `DuplicateApplicationError`, `get_application_by_idempotency_key`, and `application_exists` deduplication checks in `db.py`.
5. **[RESOLVED] Symptom 5: Missing Status Enforcement & Grounding** — Implemented 12-Phase ASP engine with strict per-phase Definition of Done (DoD) verification gates.
6. **[RESOLVED] Bonus Bug 1: CredentialVault Key Directory Failure** — Fixed `key_dir.mkdir(parents=True, exist_ok=True)` initialization in `vault.py`.
7. **[RESOLVED] Bonus Bug 2: Discovery Engine Silent Fallback** — Created unified `AdapterRegistry` mapping all 16 site adapters cleanly.
8. **[RESOLVED] Bonus Bug 3: Supervised Auto-Apply Bypasses Pipeline** — Supervised auto-apply path now routes through `pipeline.execute()` with full evidence capture.
