# Production Readiness Baseline & Scorecard

**Generated:** 2026-08-16 (Phase 0 / WS0, per `MASTER_PLAN_EXPANDED.md` Section 24)
**Commit context:** post `4435f2c` working tree (WS0 + WS1 execution session)
**Rule:** this file reports only machine-verified facts from this session's runs. Historical claims from plan documents are not repeated as truth (evidence hierarchy, MASTER_PLAN_EXPANDED.md §2.1).

## 1. Test baseline (verified 2026-08-16)

| Suite | Result | Notes |
|---|---|---|
| pytest (full) | **359 passed, 13 skipped** (372 collected), 83.5s | Pre-WS1 run. Skips = integration/live markers (opt-in) + POSIX-only hardening tests on Windows host. |
| vitest (GUI) | **18 passed** (3 files) | Pre- and post-upgrade: identical on vitest 3.2.7 and 4.1.10. |
| Coverage | **not measured** | `pytest-cov` not in dev extras; tooling gap queued (improve queue). Floor policy D23: measured −2%, min 70%. |
| Ruff | 21 F401 pre-existing across `src/` | 5 fixed in `cli/main.py` this session; CI currently `--ignore F401`; full cleanup queued (RF-1 CLI split will restructure imports anyway). |
| mypy | not run this session | strict config present; queued for G1 CI verification. |

## 2. Security baseline (verified 2026-08-16)

| Check | Before WS1 | After WS1 (this session) |
|---|---|---|
| `npm audit` | 3 vulns (2 high: nanoid GHSA-2v37-7h3g-55p8; 1 moderate: esbuild GHSA-67mh-4wv8-2f99 via vite ≤6.4.2) | **0 vulnerabilities** (vite 8.2.1, vitest 4.1.10, plugin-react 6.0.5, tauri-cli 2.11.4, nanoid transitive fixed) |
| URL sanitization | `infer_site()` substring match + silent `greenhouse` fallback; `workday._split_company` substring match (9 CodeQL `py/incomplete-url-substring-sanitization` alerts) | exact host-suffix matching via `urlsplit().hostname`; unknown → `ValueError` (D1); adversarial suite `tests/test_url_inference.py` 54 tests green |
| Vault keyfile | `open()`+`chmod` TOCTOU window; no symlink/permission checks | atomic 0600 create (`O_EXCL`+`os.replace`), `O_NOFOLLOW` reads, fail-closed perm check (POSIX); `tests/test_vault_hardening.py` 6 passed + 3 POSIX-skipped on Windows host |
| Tauri CSP | `null` | set: `default-src 'self'` + scoped script/style/img/font/connect (IPC allowed) |
| Shell plugin args | `args: true` (arbitrary) | validator `^sidecar$` (only arg the GUI ever passes) |
| CI actions pinning | tag-pinned | 20/20 `uses:` SHA-pinned across 4 workflows |
| CI security gates | none | `security-gates.yml`: pip-audit (`--strict`), npm audit (high-fail), gitleaks (full history, `.gitleaks.toml`) |
| pip-audit (local) | tooling absent on dev host | runs in CI security-gates job (ubuntu); local install deferred |
| CodeQL 9 alerts | open | root cause fixed in code (W2); alerts close on next platform scan — verify then |
| glib RUSTSEC-2024-0429 | open | accepted residual, documented in SECURITY.md (D3; tauri 2 transitive) |

## 3. Version authority (verified 2026-08-16)

Drift before: pyproject 0.1.0, root package.json 0.1.0, gui/package.json 2.0.0, tauri.conf.json 2.0.0.
After: **all 0.2.0**, canonical source `pyproject.toml`, enforced by `scripts/sync_versions.py --check` (exit 1 on drift). No stable release has shipped; 0.2.0 is the honest dev line toward v1.0.0 (release criteria in MASTER_PLAN_EXPANDED.md §23).

## 4. Known defects/debt (verified in code, from §2.2 audit; unchanged this session)

- `task_graph.py` in-memory only — durable engine is WS2 (UC-01), next workstream.
- LLM provider `stream()` stubs (7), `scrapers/ats.py`, most of `adapters/linkedin.py` → `NotImplementedError`.
- `cli/main.py` 1,748-line monolith (RF-1).
- Ad-hoc `_ensure_column` migrations, no `schema_migrations` (UC-07, WS2).
- `more_adapters.py` discover() generates synthetic postings (mock-quality adapters presented as real boards) — flagged for honest-adapter treatment (WS4).
- Zero-coverage modules: `digest/`, `notify/`, `outreach/`, `scheduler/loop.py`.
- No event bus; `AlertDispatcher` unwired; `stealth/` selectors hard-coded; `EightTierMemorySystem` skeletal.
- Root cruft: duplicate plan sets, `JoBot_Merge_Plan.pdf`, `cover.html`, `applications_export.json` (user data), 403KB `log.md` — cleanup is UC-51 (WS8).

## 5. Scorecard (0–10, evidence-linked)

| Dimension | Score | Evidence / gap |
|---|---|---|
| Functional breadth | 6 | 16 adapters (mock-quality caveat), 12-phase ASP, scheduler, GUI 5 views |
| Reliability/durability | 2 | in-memory task engine, no effect ledger, no kill-anywhere proof (WS2 target) |
| Correctness/idempotency | 3 | pipeline key exists; no `ExternalEffect` ledger; no UNKNOWN states |
| Security | 5 → 7 | WS1 landed (audit 0, URL sanitization, vault, Tauri, CI gates); CodeQL rescan + pip-audit CI pending |
| Verification/test | 5 | 359 green but no coverage floor, no failure-injection suite |
| Observability | 3 | file traces, alerts unwired, no event bus |
| Docs/governance | 4 → 6 | governance files landed this session (SECURITY/CONTRIBUTING/CHANGELOG/…); docs suite + site pending (UC-50) |
| Release engineering | 3 | publish workflow tag-pinned→SHA now; trusted publishing/SBOM/signing pending (WS9) |
| Memory/self-improvement | 1 | 8-tier skeleton only (G18/G40) |

**Overall: 4.1 / 10 → v1.0.0 target = all rows ≥ 7 with §23 checklist green.**

## 6. What must be true to close G0 (Truth)

- [x] Baselines machine-generated and committed (this file)
- [x] Test/audit numbers from live runs, not plan claims
- [x] Queues rewritten truthfully against repo state
- [x] Version authority single-sourced
