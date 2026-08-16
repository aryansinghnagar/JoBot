# Implementation Contract: Milestone dev-0.1 (Basic Architecture)

**Document ID**: CONTRACT-DEV-0.1  
**Version**: 1.0  
**Status**: Active Contract  
**Target Completion**: Milestone dev-0.1  

---

## 1. Objective
Establish the core architectural substrate for AJOS (`jobot`), including project scaffolding, canonical directory structure, Pydantic domain models, SQLite control plane DB, CredentialVault (`age` encryption), 12-phase Application Submission Pipeline (ASP), Mock ATS server, Naukri SiteAdapter (supervised mode), and Typer CLI.

## 2. In Scope
1. Repository Scaffolding:
   - Canonical directory structure: `src/jobot/`, `tests/`, `config/`, `queues/`
   - Build configuration: `pyproject.toml` with pinned dependencies
   - Quality tools: `pytest`, `ruff`, `mypy`, pre-commit configuration
   - Foundational docs: `AGENTS.md`, `README.md`, `LICENSE` (AGPL-3.0-only for core, MIT for adapters)
   - Local directory setup: `~/.jobot/` (`artifacts/`, `logs/`, `backups/`, `db/`)
2. Core Data Models (`src/jobot/models/`):
   - `UserProfile` (~340-field schema foundation)
   - `JobPosting`
   - `Application`
   - `Task` & `Goal`
   - `Evidence`
3. Storage & Vault (`src/jobot/storage/`):
   - SQLite WAL database manager & migration engine
   - `CredentialVault` using `age` cipher & OS keyring abstraction
4. Execution & Task Graph (`src/jobot/core/`):
   - Task Graph engine (`Layer C`)
   - Pull-based worker loop with atomic task locking (`Layer B`)
5. Mock ATS Server (`tests/mock_ats/`):
   - Local Flask server exposing application forms for end-to-end verification
6. Naukri SiteAdapter (`src/jobot/adapters/naukri.py`):
   - `SiteAdapter` abstract base class
   - `NaukriAdapter` with Patchright browser execution & basic rate-limiting
7. Submission Harness & CLI (`src/jobot/asp/` & `src/jobot/cli/`):
   - 12-Phase ASP state machine
   - Deterministic Q&A Engine (Profile-direct lookup)
   - Deterministic Reviewer & ApprovalGate
   - CLI commands: `setup`, `profile`, `run`, `status`, `pause`, `export`

## 3. Exit Criteria
- [ ] All `dev-0.1` phases (0.1.0 through 0.1.6) implemented
- [ ] End-to-end closed loop test passes on Mock ATS
- [ ] End-to-end closed loop cassette test passes for Naukri
- [ ] `profile.yaml` stored encrypted via `age`
- [ ] Credentials securely fetched from OS Keyring / vault
- [ ] 12-phase ASP executes with full evidence capture (`~/.jobot/artifacts/`)
- [ ] All 6 CLI commands execute without error
- [ ] Minimum 15 unit tests and 5 integration tests passing
- [ ] `ruff` and `mypy` pass with 0 errors

## 4. Sign-off Contract
This contract is normative for `dev-0.1`. Implementation must not deviate from these boundaries without updating this contract.
