# BLOCKED QUEUE — Active Impediments

The following active blockers were diagnosed in `JoBot_Refactor_Plan.md` and are actively being resolved:

1. **Symptom 1: Fake Companies in Log** — All 16 adapters return hardcoded company names and unconditional `VERIFIED` status without HTTP or browser actions.
2. **Symptom 2: Hardcoded Job Titles** — `parse_job_posting` returns hardcoded job titles and ignores input URLs.
3. **Symptom 3: Hardcoded Skill Match Scores** — `evaluate_match` operates on hardcoded 3-4 skill lists returning fixed 33%/50%/66% ratios.
4. **Symptom 4: Infinite Loop Runner Without Dedup** — `runner.py` increments `total_submitted` unconditionally and uses `INSERT OR REPLACE` which silently overwrites duplicates.
5. **Symptom 5: Missing Status Enforcement & Grounding** — Pipeline grounding checks fail to verify full form inputs and adapter verifiers unconditionally return `True`.
6. **Bonus Bug 1: CredentialVault Key Directory Failure** — `CredentialVault` custom `key_dir` does not create directory when specified, failing headless runs.
7. **Bonus Bug 2: Discovery Engine Silent Fallback** — `discovery/engine.py` `_get_adapter()` falls back to `NaukriAdapter` for 10 portals.
8. **Bonus Bug 3: Supervised Auto-Apply Bypasses Pipeline** — `auto-apply` CLI supervised mode bypasses ASP Phases 11-12 evidence recording.
