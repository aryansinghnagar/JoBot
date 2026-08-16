# AGENTS.md — Autonomous Job Application Operating System (`jobot`)

## System Identity & Doctrine

`jobot` is a local-first, privacy-preserving, human-governed autonomous job application operating system. The authoritative specification is `unified_master_plan.md` (very large — grep it rather than reading end-to-end); the architect doctrine is `agent.md`. The repo is mid-refactor: `JoBot_Refactor_Plan.md` and `JoBot_Refactor_Review_2.md` define the current work; `worklog.md` logs completed tasks.

## Non-Negotiable Core Mandates

1. **Source of Truth**: Candidate profile facts are canonical. Never hallucinate facts, applicant data, or test credentials. Meaning may be formatted/tailored, but zero invented facts.
2. **Deterministic Security**: Zero secrets in source, logs, or git commits (`.env` holds real API keys; gitignored). Profile encryption is Fernet AES-256 (`cryptography`) with the master key in the OS keyring — `src/jobot/storage/vault.py`. Not `age`, despite `operating_summary.md` and `.agents/agents.md` saying so; code is truth. Legacy keyring service `jobaut_vault` auto-migrates to `jobot_vault`.
3. **Idempotent Actions**: Every submission carries an idempotency key / effect identity (`tests/test_dedup.py` enforces rejection of duplicates).
4. **Reliability First**: 12-phase ASP pipeline (`src/jobot/asp/pipeline.py`) with per-phase DoD verification gates, circuit breakers, daily policy caps, and evidence capture.
5. **Closed-Loop Execution**: Verify with the test suite before declaring work complete.

## Python Commands

```sh
pip install -e .[dev]                          # dev extras: pytest, pytest-asyncio, ruff, mypy, flask
pytest                                         # asyncio auto-mode; testpaths=tests
pytest tests/test_storage.py                   # single file / dir (e.g. tests/integration/)
ruff check src/ --select E,F --ignore E501,F401
ruff format --check src/                       # line-length 100; LF enforced via ruff + .gitattributes
mypy src/ --ignore-missing-imports             # pyproject sets strict=True
```

CI (`ci.yml`) runs exactly these gates on `main`/`dev` pushes and PRs (Py 3.11/3.12, 3 OSes). `ruff`/`mypy` only cover `src/`, not `tests/`.

## JS Test Suite (Dual Stack)

```sh
npm ci
npm run test    # vitest — tests/npm/system.test.js
npm run lint    # prettier --check
```

## Test Gotchas

- The mock ATS Flask server auto-starts on port 5800 via the session fixture in `tests/conftest.py` — no manual setup. `tests/integration/`, `test_asp*.py`, and `test_mock_ats_integration.py` hit it live.
- Eval definitions live as JSON in `tests/evals/` (grounding, PII, daily-cap, circuit-breaker checks); runnable via `jobot evals`.
- Browser/CAPTCHA tests require `patchright` and a usable browser environment.

## Architecture Notes

- The only entrypoint is the `jobot` console script (no `__main__.py`). Key commands: `setup`, `profile init/show`, `auto-apply`, `continuous-campaign`, `run`, `status`, `pause`, `resume`, `export`, `schedule`, `traces`, `alerts`, `evals`, `login`, `reset-db`, `sidecar`.
- Profile lives at `~/.jobot/profiles/default.enc` (Fernet-encrypted JSON). Commands must error out cleanly when the profile is missing — never hardcode a fallback identity.
- Site adapters: `src/jobot/adapters/` — registry of ~16 portals (greenhouse, indeed, lever, linkedin, workday, mock_ats, naukri, ...); submissions are supervised by default.
- AI routing: `src/jobot/ai/router.py` `ModelRouter` — Gemini primary (`google-genai`), OpenAI/Anthropic/Ollama fallback. Extracted skills are persisted to `state/profile/skills.md`.
- Stealth: patchright browser sessions (`src/jobot/stealth/`), circuit breaker with exponential backoff, CAPTCHA vision solver, behavioral mimicry.
- Storage: SQLite WAL control plane + Fernet vault; `applications_export.json` is a campaign export artifact.

## Workflow Conventions

- Task tracking lives in `queues/` markdown momentum queues (`now.md`, `next.md`, `blocked.md`, `improve.md`, `recurring.md`) — update them when taking on or landing work.
- Commit style: section-tagged conventional commits, e.g. `[CI/CD] ...`, `[Refactor] ...`, `[Master Plan Phase X] ...`.
- CI runs on branches `main` and `dev`; locally only `main` exists.
- `log.md` at repo root is the campaign run log and is gitignored.
- `.agents/agents.md` is auto-loaded but partially stale (claims `age` and `black --check`; CI actually uses Fernet and `ruff format`).