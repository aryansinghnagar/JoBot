# IMPROVE QUEUE — Improvement Candidates & Subsystem Wiring

## Improvement candidates (MASTER_PLAN_EXPANDED.md §10.4/§15; one-change rule applies)

1. ~~`tests/test_imports.py` undeclared-deps guard~~ — **DONE 2026-08-16** (117 import checks green; jobspy remains the documented deliberate lazy exception).
2. **RF-1 slice:** split 1,748-line `cli/main.py` into subcommand modules (signatures frozen; `main.py` < 100 lines).
3. **Property-based tests** (`hypothesis`) for PII masker patterns.
4. **Typed error taxonomy** replacing `except Exception: pass` / `BLE001` swallowing in adapter fallbacks, stealth, sidecar.
5. **Coverage tooling:** add `pytest-cov` to dev extras, measure, set floor (D23: measured −2%, min 70%).
6. **Ruff F401 cleanup:** ~16 remaining unused imports across `src/` (5 already fixed in `cli/main.py`); drop CI `--ignore F401` once zero.
7. **`more_adapters.py` honesty pass:** discover() fabricates synthetic postings for 9 boards (glassdoor/ziprecruiter/shine/foundit/hirist/instahyre/cutshort/wellfound/smartrecruiters) — mark mock-quality in `list-sites`/docs or implement real discovery (G42-adjacent; honesty invariant).
8. **Zero-coverage modules:** `digest/`, `notify/`, `outreach/`, `scheduler/loop.py`.

## External intelligence (weekly digest cadence)

- Study Temporal durable execution patterns for task graph (UC-01) — priority study per MASTER_PLAN_EXPANDED.md §16.1.
- Test DSPy optimizer for prompt improvement (Mode 2 self-improvement).
- PydanticAI boundary schemas — already on Pydantic v2 (adopted).

## Stale assumptions to re-verify

- ~~"359 tests" baseline~~ — verified 2026-08-16: 372 collected → 359 passed + 13 skipped (matches).
- ~~"release 2.0 tagged" vs pyproject 0.1.0~~ — resolved: versions unified at 0.2.0, `sync_versions.py --check` enforces.
- ~~"Patchright integration in progress" README staleness~~ — README rewrite queued under UC-47/UC-50 docs suite (root README still stale).

## Subsystem wiring status (reconciled 2026-08-16 against worklog + code)

Previously listed 9 "unwired" items — reconciled:

1. ~~QAEngine into ASP phases~~ — WIRED (asp pipeline; tests green).
2. ~~PolicyEngine into runner~~ — WIRED (scheduler caps; `test_policy_cap.py`, `test_policy_enforced.py`).
3. ~~CircuitBreaker around adapters~~ — WIRED (`stealth/circuit_breaker.py`; dead duplicate removed).
4. ~~TraceLogger spans~~ — WIRED (`test_tracing_wired.py`).
5. ~~AlertDispatcher~~ — WIRED to incidents (`test_alerts_wired.py`) — **upgrade pending:** wire to scheduler/GUI via event bus (AR-7).
6. **EightTierMemorySystem / form_field_memory persistence** — OPEN (persist tier; reuse in `fill_form`; becomes answer bank UC-26/F-02).
7. **BehavioralMimicry** — OPEN (Bezier math fix; wire into browser adapters; compliance-bounded).
8. **ProxyManager into browser context init** — OPEN (config keys; ToS-gated, default off).
9. **CaptchaSolver vision path** — OPEN (multimodal bytes -> LLM vision; detection/escalation boundary only — never a bypass).
