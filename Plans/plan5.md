# JoBot Vulnerability & Issue Remediation Plan (plan5)

**Version:** 1.0 · 2026-08-15 · Status: APPROVED-PENDING-EXECUTION
**Scope:** fix every vulnerability, code-scanning issue, and other issue found by GitHub (Dependabot, CodeQL), online audits (npm audit, crates.io/RUSTSEC), and independent analysis (AST dependency audit, git history secret scan, CI/workflow inspection, code review).
**Companion docs:** [`Plan3.md`](./Plan3.md) (master plan) · [`plan4.md`](./plan4.md) (production readiness) — items overlapping plan4 are executed here and referenced, not duplicated.

## 1. Approved Decisions (D-1 … D-4)

| # | Decision | Default |
|---|---|---|
| D-1 | `infer_site()` unknown URLs | Raise explicit `ValueError` instead of silently defaulting to `greenhouse` |
| D-2 | vite upgrade | Major upgrade `5.4.21 → 8.2.1` (only clean fix; vite 6.4.3 leaves esbuild vulnerable) |
| D-3 | glib GHSA-wrw7-89jp-8q8g | Accepted as documented residual risk (no fix in tauri 2 tree); monitored via Dependabot + `cargo audit` |
| D-4 | Execution order | W1 → W2 → W4 → W7 → W6 → W5 → W8 → W9 → W3 → W10 |

## 2. Verified Baseline & Findings (2026-08-15)

### A1. Dependabot — 5 open alerts (1 high, 4 moderate)

| # | Package | Vulnerability | Our version | Fix |
|---|---|---|---|---|
| 1 | vite (npm, dev) | CVE-2026-53571 **high** — GHSA-fx2h-pf6j-xcff, `server.fs.deny` bypass on Windows alternate paths | 5.4.21 | 8.2.1 |
| 2 | vite (npm, dev) | CVE-2026-53632 — GHSA-v6wh-96g9-6wx3, launch-editor NTLMv2 hash disclosure via UNC path | 5.4.21 | 8.2.1 |
| 3 | vite (npm, dev) | CVE-2026-39365 — GHSA-4w7w-66w2-5vf9, path traversal in optimized deps `.map` | 5.4.21 | 8.2.1 |
| 4 | esbuild (npm, dev) | GHSA-67mh-4wv8-2f99 — dev server lets any website read responses | 0.21.5 | ≥0.25 (dropped via vite 8 / rolldown) |
| 5 | glib (rust, runtime) | GHSA-wrw7-89jp-8q8g / RUSTSEC-2024-0429 — `VariantStrIter` unsoundness, NULL-deref crash | 0.18.5 (tauri 2.11.5 / gtk3) | 0.20.0 — **unresolvable in tauri 2** (see W3) |

Also verified:
- `nanoid` 3.3.17 **high** (GHSA-2v37-7h3g-55p8, <3.3.18) — alert auto-dismissed but lockfile still vulnerable; re-verify post-upgrade (W1)
- vitest critical (GHSA-5xrq-8626-4rwp) — already fixed (resolved 3.2.7 ≥ 3.2.6)
- `npm audit` local: 3 vulnerabilities (vite high, nanoid high, esbuild moderate); `fixAvailable: vite 8.2.1 (semver major)`

### A2. CodeQL — 9 open alerts, all `py/incomplete-url-substring-sanitization`

| Location | Issue |
|---|---|
| `src/jobot/adapters/registry.py:28` (×2), 30, 32, 34, 36, 38, 40 | `infer_site()` substring matching (`"greenhouse.io" in lowered`, …) — crafted URLs (`greenhouse.io.attacker.com`, `evil.com/?q=lever.co`) misclassify → misrouted discovery |
| `src/jobot/adapters/workday.py:95` | `"myworkdayjobs.com" in lowered` on user-supplied company string |

(Previously fixed: `cli/main.py` URL checks, missing-workflow-permissions in ci.yml/publish.yml.)

### A3. GitHub repo hygiene

- Missing: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `FUNDING.yml`, issue/PR templates, `CODEOWNERS`
- Dependabot: no `cargo` ecosystem (how glib went unnoticed), no groups, `open-pull-requests-limit: 10` daily
- Actions not SHA-pinned; CodeQL analyzes only python+javascript (rust missing); CI node matrix 18/20 — both EOL; workflows trigger on `dev` branch that does not exist; `publish.yml` uses token auth (not trusted publishing)
- Settings (manual, unverifiable via token): secret-scanning push protection, Dependabot security updates, branch protection

### A4. Independent analysis

1. CI ruff invocation too narrow: `--select E,F --ignore E501,F401` masks regressions; `black` installed but unused
2. mypy `python_version = "3.12"` vs `requires-python >=3.11`
3. `pyproject.toml`: deprecated `license = {text=...}`; no classifiers/urls/keywords; version 0.1.0 vs gui 2.0.0 / tauri.conf 2.0.0 drift (4 files)
4. `tauri.conf.json`: `csp: null`; bundle icon only `icon.png`; no updater/code-signing (plan4 R2.5–R2.7)
5. Capabilities `default.json`: `shell:allow-spawn/execute` with `args: true` — unrestricted args
6. `vault.py`: keyfile fallback written 0644-then-chmod window; no owner/mode check on read (trusts world-readable keyfiles); symlink-follow on write; Windows no ACL enforcement
7. Undeclared dependency AST scan (27 modules): clean — `jobspy` only undeclared import, deliberately (pins numpy==1.26.3; `--no-deps` recipe in SETUP.md; import-guarded); `google`/`boto3` accounted for
8. `infer_site()` default silently returns `greenhouse` for unknown URLs → D-1
9. Git history secret scan: clean (no matches)
10. README stale ("Patchright integration in progress", no badges); LICENSE lacks copyright holder line; `.gitignore` missing `.venv/`, `*.p12`, `.coverage.*`; `Plan1.pdf` (100 KB binary) at repo root

## 3. Fix Plan (priority-ordered work packages)

### W1 — npm stack upgrade (release-blocking; closes Dependabot 1–4 + nanoid)
1. `package.json`: `vite ^5.4.11 → ^8.2.1`; `vitest ^3.2.7 → ^4.1.10` (peer vite ^6\|\|^7\|\|^8); `@vitejs/plugin-react ^4.3.4 → ^6.0.5` (peer vite ^8); `prettier → ^3.9.6`; `@tauri-apps/api ^2.1.1 → ^2.11.1`, `@tauri-apps/cli ^2.1.0 → ^2.11.4`, `@tauri-apps/plugin-shell → ^2.3.x`
2. `npm install`; verify `npm audit` = 0 vulnerabilities; verify nanoid ≥ 3.3.18 (add `overrides` if residue); esbuild gone via rolldown
3. Re-run `npm run test` (18 tests) + `npm run build:gui`; fix vitest 4 / vite 8 drift if any (config explicitly sets `include` — low risk)
4. Add `engines: {"node": ">=20.19.0"}` + `packageManager` to root `package.json`
5. CI npm matrix `18/20 → 20/22` (vite 8 requires `^20.19.0 || >=22.12.0`)
- **Verify:** `npm audit` clean; vitest 18/18; vite build OK; Dependabot alerts 1–4 close

### W2 — CodeQL URL sanitization (release-blocking; closes 9 alerts)
1. Rewrite `infer_site()` in `src/jobot/adapters/registry.py`: `urllib.parse.urlsplit` → exact netloc match or `host == x or host.endswith("." + x)`; strip port/userinfo; unknown → raise `ValueError` (D-1)
2. Fix `workday.py:95`: parse company as host/URL; match exact host or `WORKDAY_HOST_RE` only
3. New `tests/test_url_inference.py` adversarial cases: `greenhouse.io.attacker.com`, `https://evil.com/?q=lever.co`, `myworkdayjobs.com.evil.org`, port/userinfo tricks, uppercase, trailing-slash, scheme-less hosts
4. Update CLI/sidecar callers to surface the new `ValueError` cleanly (no stack trace in GUI)
- **Verify:** new tests green; full suite green; CodeQL re-scan → all 9 close

### W3 — glib RUSTSEC-2024-0429 (accepted residual risk; no fix in-tree)
1. Document in `SECURITY.md` risk register: unreachable code path (VariantStrIter never used), Linux/macOS-only transitive dep via tauri/gtk3, EPSS 0%, fixed in glib 0.20 = tauri 3/gtk4
2. Add `cargo` ecosystem to Dependabot; add `cargo audit` (or `cargo deny`) job to desktop CI when it lands (plan4 R2.3)
3. Re-evaluation trigger: tauri ≥ 3 or gtk4 migration
- **Verify:** documented; Dependabot cargo updates active

### W4 — CI hardening
1. Ruff: drop narrow `--select E,F --ignore E501,F401`; use pyproject defaults (`ruff check src/`); remove unused `black` install
2. Pin tool installs (ruff/mypy/pytest-cov/cyclonedx-bom) to versions aligned with pyproject `[dev]`
3. New `security-gates` job: `npm audit --audit-level=high`, `pip-audit`, `gitleaks` (full history), `actionlint`
4. SHA-pin all `actions/*@vN` → commit hashes (checkout, setup-python, setup-node, upload-artifact, codeql-action, attest-build-provenance); ensure `permissions: contents: read` top-level on all jobs
5. CodeQL matrix: add `rust` (covers `gui/src-tauri`)
6. `dev` branch cleanup: create branch or trim workflow triggers to `[main]`
7. Publish workflow: switch to trusted publishing (`id-token: write`, environment `pypi`) — from plan4 R2.1
8. Add `tests/test_imports.py`: import every src module with base install (no extras) — guards undeclared-deps regressions
- **Verify:** all CI jobs green; `actionlint` clean; gitleaks 0 findings; pip-audit clean

### W5 — Tauri/GUI hardening
1. CSP: replace `"csp": null` with restrictive default (script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' ipc: http://ipc.localhost) — plan4 R2.8; verify `tauri:dev` + `tauri:build` clean, no console CSP violations
2. Capabilities: replace `args: true` with regex allowlist (`^sidecar$`, `^--[a-zA-Z0-9-]+(=.*)?$`-style) for spawn and execute
3. Explicit `"label": "main"` on the window; icons per plan4 R2.4; updater + signing per plan4 R2.5–R2.7 (referenced, executed there)
- **Verify:** dev/build run clean; capability validation passes

### W6 — Python packaging & metadata
1. `license = "AGPL-3.0-only"` SPDX string (kills setuptools ≥77 deprecation); add `classifiers`, `keywords`, `[project.urls]` (homepage, docs, source, issues)
2. mypy `python_version = "3.11"` (match lowest supported)
3. Version sync: `scripts/sync_versions.py` aligns pyproject / root package.json / gui package.json / tauri.conf.json (plan4 R1.1); verify all four now
- **Verify:** `python -m build` clean; `twine check` clean; sync script idempotent

### W7 — Vault hardening
1. Create keyfile with `os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)` (no chmod-after-write window); on POSIX refuse reading keyfiles not owned by uid or with group/other bits set
2. `O_NOFOLLOW` on POSIX open for keyfile read/write (symlink attack); Windows: document ACL reliance in code comment + SECURITY.md
3. New `tests/test_vault_hardening.py`: world-readable keyfile rejected, symlinked keyfile refused, perms enforced at creation
- **Verify:** hardening tests green; existing vault tests unaffected

### W8 — Governance files (plan4 R1.6 — executed here)
`SECURITY.md` (vulnerability reporting + PGP, glib risk register, telemetry privacy pointer), `CONTRIBUTING.md` (runbook from plan4 R5.2), `CODE_OF_CONDUCT.md`, `FUNDING.yml` (sponsorship), issue templates (bug/feature/security), PR template, `CODEOWNERS`
- **Verify:** files render on GitHub; CONTRIBUTING runbook executable

### W9 — Hygiene & docs
1. README overhaul (plan4 R1.8): badges, quickstart, architecture, honest adapter status ("Patchright integration in progress" removed)
2. LICENSE: add copyright holder line ("Copyright (C) 2026 JoBot contributors")
3. `.gitignore` += `.venv/`, `*.p12`, `.coverage.*`
4. jobspy caveat: document in README + `jobot doctor` warning when `jobspy` missing and a scraper board is requested
5. Move `Plan1.pdf` → `docs/` (keep `Plan1.md`, `Plan2.md`, `Plan3.md`, `plan4.md`, `plan5.md` at root)
6. Dependabot: add `cargo` ecosystem; add `groups` (batch minor/patch)
- **Verify:** files consistent; no stale claims

### W10 — Repo settings (manual, user)
Enable in repo settings: secret-scanning push protection, Dependabot security updates, branch protection on `main` (require CI green + 1 review)
- **Verify:** settings screens show enabled

## 4. Verification Protocol

- Every W ends with: gates green (pytest 359/13, ruff, mypy, vitest 18/18, prettier, npm audit clean) + worklog row + queues update
- Post-execution: re-query GitHub Dependabot + CodeQL APIs → assert 0 open alerts; `npm audit` → 0; `pip-audit` → 0
- No release tag until W1, W2, W4 pass (release-blocking); W3–W10 are hardening, completed before or with plan4 R5

## 5. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| vite 8 / rolldown breaks GUI build or vitest 4 changes behavior | Build + tests run in W1 before proceeding; revert if unresolvable, then escalate (documented residual) |
| CodeQL re-scan flags new patterns after refactor | Fix incrementally; one-change loops per AGENTS.md |
| `infer_site` ValueError breaks CLI/sidecar UX | Surface clean error message + `jobot list-sites` guidance (W2 step 4) |
| glib alert remains open (no fix) | Documented in SECURITY.md; Dependabot cargo + cargo audit monitor; alert auto-closes when tauri bumps |
| npm audit gate fails on transitive dev-dep | `overrides` for nanoid if needed; escalate before tag |

## 6. Interlock with Existing Plans

- plan4 R1.1 (version sync) → W6.3 · R1.3 (coverage gate) unchanged · R1.4 (audit gates) → W4.3 · R1.5 (actions hardening) → W4.4 · R1.6 (governance) → W8 · R1.7 (license) → W9.2 · R1.8 (README) → W9.1 · R2.1 (trusted publishing) → W4.7 · R2.4–R2.7 (icons/updater/signing) referenced by W5.3 · R2.8 (CSP) → W5.1
- Plan3 A.2 (AR-2 selector registry) untouched; W2 is independent (URL classification only)