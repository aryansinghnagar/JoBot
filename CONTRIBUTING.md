# Contributing to JoBot

JoBot is an autonomous job-application agent: a Python 3.11+ core (Typer CLI,
Pydantic v2, SQLite WAL, Patchright browser) with a Tauri 2 / React 18
desktop GUI in `gui/` that talks to the core over a JSON-RPC sidecar
(`jobot sidecar` in `src/jobot/gui/sidecar.py`).

Contributions of any size are welcome, especially reproducible bug reports,
adapter improvements, and tests. This document covers setup, checks, and the
project's conventions. The canonical architecture and roadmap live in
`MASTER_PLAN_EXPANDED.md`.

## Development Environment Setup

Prerequisites:

- Python **3.11+** (CI tests 3.11, 3.12, and 3.13 on Linux, Windows, and macOS)
- Node.js **20+** (matches `package.json` `engines.node >= 20.19`; needed for vitest/prettier gates; a Rust toolchain is only needed for the local Tauri desktop build — see `SETUP.md` Section 7)

```bash
# 1. Clone
git clone https://github.com/aryansinghnagar/JoBot.git
cd JoBot

# 2. Create and activate a virtualenv (Windows: .venv\Scripts\activate)
python -m venv .venv
source .venv/bin/activate

# 3. Install the Python package with dev + scrapers extras
python -m pip install -e ".[dev,scrapers]"

# 4. Install Node dependencies (single root package.json covers CI and GUI)
npm ci
```

For the full first-run experience (Patchright browser install, `jobot init`,
OS keyring configuration, provider API keys) follow `SETUP.md` Section 2 —
`jobot doctor` should report a healthy environment before you debug anything
else.

## Running the Checks

Run these before opening a pull request. CI (`.github/workflows/ci.yml`)
runs the same gates on three operating systems.

| Check | Command | Notes |
| --- | --- | --- |
| Python tests | `python -m pytest -q` | Full suite; live-scrape tests are opt-in (see below) |
| Python lint | `ruff check src/` | CI runs ruff with the expanded rule set in `pyproject.toml` (`E,F,W,S,B,C90,UP,I`) — see the `[tool.ruff.lint]` block for the current ignore list |
| Python formatting | `ruff format --check src/` | Enforced; run `ruff format src/` to fix |
| Static types | `mypy src/` | Strict config in `pyproject.toml`; CI adds `--ignore-missing-imports` |
| JS tests | `npm test` | `vitest run` over `tests/npm` and `gui/tests` |
| JS formatting | `npm run lint` | `prettier --check`; run `npm run format` to fix |

Opt-in live tests are excluded from normal runs via pytest markers
(`integration`, `scrapers`):

```bash
# Live scraper tests (real network calls):
JOBOT_RUN_LIVE_SCRAPE=1 python -m pytest tests/ -m scrapers

# Live browser adapter tests (real browser automation against real sites):
JOBOT_RUN_LIVE_BROWSER=1 python -m pytest tests/integration/
```

Do not enable these flags in CI-facing work without coordinating with the
maintainer; they are slow and touch third-party services.

## Verification-First Culture

Nothing is "done" because the author says so. A change is done when its
verification passes and the evidence is in the pull request:

- **Every bug fix and feature ships with tests** (or an explicit explanation
  of why testing it is impossible and what manual evidence replaces it).
- **Adapters never fabricate results.** When a live capability is unavailable
  (no API, live browser disabled), adapters must report an honest no-op
  status rather than inventing a plausible outcome. This is a core project
  invariant — see `docs/contracts.md` for the frozen interfaces.
- **Provide evidence in the PR:** exact commands run and their summarized
  results. The pull request template asks for this explicitly.
- The full verification doctrine (levels L1-L9, phase gates G0-G7) is
  specified in `MASTER_PLAN_EXPANDED.md` Section 6.

## Branch and Pull Request Conventions

- **Branch from `main`** using short-lived feature branches named for the
  change, e.g. `fix/naukri-card-parser`, `feat/workday-cxs-health`,
  `docs/setup-cli-tables`.
- **One logical change per PR.** A refactor and the feature built on it are
  two PRs; a fix and its regression test are one.
- **Small diffs review faster.** If a PR touches more than ~400 lines of
  non-test code, consider splitting it.
- **Reference the issue.** Open an issue first for bugs and features, then
  link it in the PR (`Closes #N`).
- **Fill in the PR template** (`.github/PULL_REQUEST_TEMPLATE.md`):
  summary, related issue, what changed, how it was verified, and the
  checklist (tests, docs, no secrets, changelog entry for user-facing
  changes).
- **Never commit secrets** — API keys, cookies, session tokens, profile
  data. Secrets belong in the OS keyring via `jobot config set`
  (see `SECURITY.md`). CI and history are gitleaks-checked.
- **Do not force-push to `main`** and do not push directly to it; all
  changes land through reviewed PRs.

### Commit Messages

Any consistent, searchable style is accepted. The history mixes
`[Phase N] ...` planning tags and Conventional Commits
(`feat:`, `fix:`, `docs:`); for new work prefer Conventional Commits with a
scope, e.g. `fix(adapters): reject unknown sites in infer_site()`.

## Licensing

The core system is licensed **AGPL-3.0-only** and site adapters are **MIT**
(`LICENSE`, `README.md`). By submitting a pull request you agree that your
contribution is licensed under the same terms as the files you modify
(AGPL-3.0-only for `src/jobot/` outside adapters, MIT for adapter code,
AGPL-3.0-only or the prevailing license for everything else). If your change
spans both license zones, say so in the PR.

## Release Roles and Versions

- **Maintainer / release role:** @aryansinghnagar (sole maintainer; owns
  tagging, CI, and repository settings).
- **No stable release has shipped.** `pyproject.toml` is at `0.2.0`;
  the `release-1.0-alpha`, `release-1.0`, and `release-2.0` git tags are
  internal development milestones, not published distributions. Version
  bumps and changelog curation are maintainer-driven — see `CHANGELOG.md`.
- User-facing changes should add an entry under **Unreleased** in
  `CHANGELOG.md` (Keep a Changelog format).

## Where to Look Next

- `SETUP.md` — installation, configuration and secrets, Docker, CLI
  reference, troubleshooting
- `README.md` — project overview and architecture summary
- `docs/README.md` — documentation index: the authoritative merge plan,
  the 12-phase Application Submission Pipeline (`docs/asp.md`), and frozen
  interface contracts (`docs/contracts.md`)
- `docs/dev/architecture.md` — developer architecture notes
- `docs/user/cli-reference.md` — CLI reference
- `MASTER_PLAN_EXPANDED.md` — canonical expanded plan (risk register,
  decisions, verification doctrine)
- `SECURITY.md` — reporting vulnerabilities, secure configuration, accepted
  residuals
- `CODE_OF_CONDUCT.md` — community standards

## Getting Help

Open a GitHub issue (bug report or feature request templates are provided;
blank issues are disabled to keep reports actionable). For security matters,
use private vulnerability reporting — never a public issue (see
`SECURITY.md`).
