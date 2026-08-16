# NEXT QUEUE — Ready to Run (per MASTER_PLAN_EXPANDED.md Section 24; WS1 → G1 verification → WS2)

## G1 close-out (immediate)

- [ ] Full-suite verification run after WS1 landing: `python -m pytest -q`, `npm test`, `npm run lint`, `python scripts/sync_versions.py --check` — record in worklog + `artifacts/gates/G1.json`.
- [ ] Verify 9 CodeQL `py/incomplete-url-substring-sanitization` alerts close on next scan (root cause fixed in `registry.py` + `workday.py`).
- [ ] Remove unused `black` dev dependency (plan5 W4 leftover).
- [ ] `publish.yml`: switch PyPI upload to trusted publishing (needs PyPI project config — coordinate with owner; see blocked queue).

## WS2 Durable core (gate G2) — next workstream

- [ ] UC-07: `schema_migrations` table + versioned migration runner replacing `_ensure_column`; `jobot db migrate|status` CLI; migration tests.
- [ ] UC-01: durable task engine — `tasks`/`task_attempts`/`task_leases`/`task_dependencies`/`task_artifacts` tables (DDL in MASTER_PLAN_EXPANDED.md §30.1), atomic claim (§6.4), heartbeats, lease expiry reclaim, kill-anywhere-at-every-phase test.
- [ ] UC-02: append-only event ledger `task_events` with correlation/causation ids + audit/replay tests.
- [ ] UC-03: `external_effects` idempotency ledger — unique idempotency key, reservation protocol, duplicate-submission-impossible test.
- [ ] UC-05: durable `approval_requests` entity + CLI (`approval list/decide`) + sidecar RPC; survives restart test.

## Foundation quick wins (post-G1, parallelizable)

- [ ] Wire `scripts/sync_versions.py --check` into CI (drift-fail step in `ci.yml`).
- [ ] Coverage floor: measure (add `pytest-cov` to dev extras), set `--cov-fail-under` at measured −2% (min 70%).
- [ ] `.gitignore` additions (`.venv/`, `*.p12`, `.coverage.*`, `*.pem`, `*.key`, `htmlcov/`, `*.log`, `*.db-journal`, `__pycache__/`, `*.pyc`, `gui/src-tauri/target/`, `.DS_Store`).
- [ ] Local gates scripts `scripts/gates.{sh,ps1}`.
- [ ] `docs/implementation/requirements-matrix.md` from MASTER_PLAN_EXPANDED.md Section 4 UC catalog.

## Older follow-ups still open

- [ ] Naukri real submit/verify (P1.1/P1.2) — live opt-in.
- [ ] Real app icon (`npm run tauri icon`).
- [ ] `cargo check` once a C toolchain exists (or first desktop CI run closes it).
