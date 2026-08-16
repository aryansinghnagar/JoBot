# AGENTS.md — Autonomous Job Application Operating System (`jobot`)

## System Identity & Doctrine
`jobot` is a local-first, privacy-preserving, human-governed autonomous job application operating system built according to the doctrine in `agent.md` and the authoritative specification in `unified_master_plan.md`.

## Non-Negotiable Core Mandates
1. **Source of Truth**: The candidate's `profile.yaml` is canonical. Generated content must be strictly grounded in profile facts. Meaning may be formatted/tailored, but zero facts may be hallucinated or invented.
2. **Deterministic Security**: Zero secrets in source code, logs, or git commits. `profile.yaml` and API keys are stored encrypted via `age` and OS keyring.
3. **Idempotent Actions**: Every application submission carries a unique effect identity and idempotency key to prevent accidental duplicate submissions.
4. **Reliability First**: Every ASP phase has a strict Definition of Done (DoD). Per-step verification gates enforce high reliability across the 12-phase pipeline.
5. **Code Style & Quality**: Python 3.11+ using explicit type hints, Pydantic v2 schemas, `ruff` for formatting/linting, and `mypy` for static type enforcement.
6. **Closed-Loop Execution**: Always verify work with automated tests (`pytest`) before declaring completion.
