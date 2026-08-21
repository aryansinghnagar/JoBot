# Repository Execution Rules & Code Hygiene Doctrine (`.agents/agents.md`)

## System Identity & Core Mandates

This repository (`jobot`) is a local-first, privacy-preserving autonomous job application operating system built across Python (`pip`) and JavaScript/TypeScript (`npm`) modules. All future agent sessions MUST strictly adhere to the following rules:

---

## 1. Code Hygiene & Quality Standards

- **Zero Hallucinated Facts**: Candidate profile facts (`profile.yaml` / encrypted vault) are canonical. Never hallucinate facts, applicant data, or test credentials.
- **Dual-Stack Formatting & Linting**:
  - **Python (`pip`)**: Code must pass `ruff check`, `ruff format --check`, and strict `mypy` type checking. All functions must contain explicit Python 3.11+ type annotations.
  - **JS/TS (`npm`)**: Code must pass Prettier formatting checks and Vitest unit tests.
- **Clean Architecture & Decoupling**: Keep domain logic isolated from adapter layer UI bindings. Maintain single responsibility and avoid circular module imports.

---

## 2. Algorithmic Complexity & Performance

- **Sub-quadratic Execution**: Avoid nested loops `O(N^2)` over large lists of job postings or application history. Use set lookups, dictionary indexes, or database queries indexed by primary/unique keys.
- **Resource Management & Leaks**: Explicitly close database connections, HTTP client sessions, and browser contexts. Never block main async event loops with sync IO.
- **Idempotency & Deduplication**: Every external application submission MUST carry a unique idempotency key to prevent accidental duplicate actions.

---

## 3. Mandatory Test Coverage & Verification

- **Closed-Loop Verification**: Never declare work finished without executing automated test suites.
- **Python**: Run `pytest -v` with coverage check (`pytest --cov=jobot`).
- **JavaScript/TypeScript**: Run `npm test` (Vitest) ensuring all tests pass cleanly.
- **Regression Prohibition**: Never delete failing tests or lower coverage thresholds to pass CI. Fix underlying broken contracts.

---

## 4. Deterministic Security & Secrets Hygiene

- Zero API keys, tokens, or plain-text credentials in source code, logs, or git commits.
- Secure secrets via Fernet symmetric encryption (`~/.jobot/vault.enc`) and OS native keyring.
