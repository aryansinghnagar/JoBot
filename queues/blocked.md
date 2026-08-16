# BLOCKED QUEUE — Active Impediments & Review 2 Findings

Status of findings from `JoBot_Refactor_Review_2.md`:

1. **[RESOLVED - P0.1] Missing `Dict` Import in `obs/alerts.py`** — Added `Dict` to typing imports.
2. **[RESOLVED - P0.2] Missing `json`/`datetime` Imports in `cli/main.py`** — Added imports; `jobot pause`, `resume`, `export` verified.
3. **[RESOLVED - P0.3] Greenhouse URL Parser Bug & Error Handling** — Passed `application.job_url` and set `ApplicationStatus.FAILED` on HTTP submission errors.
4. **[RESOLVED - P0.4] Premature `release-1.0` Tag & State Docs** — Tag retracted (`git tag -d release-1.0`). State documentation synchronized.
5. **[RESOLVED - P0.5] EvalHarness mkdir Permission Exception** — Wrapped in try/except block.
6. **[RESOLVED - P1.7] AdapterRegistry Silent Fallback** — Replaced silent Naukri fallback with explicit `ValueError`.
7. **[RESOLVED - P1.8] Duplicate Schedule Decorators** — Removed duplicate simple `schedule_cmd`.
8. **[RESOLVED - P1.9] Duplicate Flask Fixtures** — De-duplicated `mock_ats_server` fixtures in `test_asp.py` and `test_qa_engine_wired.py`.
9. **[RESOLVED - P1.10] Duplicate CircuitBreaker** — Removed dead `CircuitBreaker` in `failure/catalog.py` in favor of canonical `stealth/circuit_breaker.py`.
10. **[RESOLVED - P2.6] CLI Command Test Coverage** — Built `tests/test_cli_commands.py`.
