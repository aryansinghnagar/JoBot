# Local Operating Summary — AJOS (Autonomous Job Application Operating System)

## 1. Default Architecture
- **Language & Runtime**: Python 3.11+, local-first execution.
- **Frontend / Interface**: Typer CLI + Tauri 2.x (Rust shell + React frontend with vanilla CSS design system). Local IPC over HTTP/stdio JSON-RPC with loopback token auth.
- **Browser Automation**: Patchright (stealth Playwright fork) for Chromium, Camoufox (anti-fingerprint Firefox) for high-hostility portals, raw CDP fallback.
- **LLM Subsystem**: Provider-neutral `ModelRouter` (Gemini 2.5/3.0 primary via `google-genai`, OpenAI/Anthropic fallback, local Ollama fallback).
- **Data & Storage**: Local filesystem-first state (Markdown momentum queues) + SQLite WAL database (`~/.jobot/jobot.db`, mode 0600) + `age` encrypted profile & credentials (`profile.yaml`) integrated with OS Keyring.
- **Submission Engine**: 12-Phase Application Submission Pipeline (ASP) state machine with idempotency keys, evidence capture, deterministic verification, and compensating rollback actions.

## 2. First Milestone: dev-0.1 (Basic Architecture)
- **Objective**: Prove the complete application-assistance loop on Mock ATS and establish the closed loop on Naukri end-to-end (supervised mode).
- **Phases**:
  1. **Phase 0.1.0**: Implementation Contract & Research Ledger
  2. **Phase 0.1.1**: Scaffolding (`pyproject.toml`, `pytest`, `ruff`, `mypy`, `.gitignore`, `AGENTS.md`, `README.md`, `~/.jobot/` structure)
  3. **Phase 0.1.2**: Core Data Model (Pydantic schemas for UserProfile, JobPosting, Application, Task, Goal; SQLite control plane DB; Task graph engine; Worker loop)
  4. **Phase 0.1.3**: Profile & Vault (`CredentialVault` with `age` encryption, OS keyring access, profile management, snapshot mechanism)
  5. **Phase 0.1.4**: Mock ATS (Flask mock server for local closed-loop testing)
  6. **Phase 0.1.5**: Naukri Adapter (`SiteAdapter` ABC, `NaukriAdapter`, basic rate-limiting/jitter, evidence capture)
  7. **Phase 0.1.6**: ASP + CLI (12-phase ASP state machine, profile-direct Q&A engine, deterministic Reviewer, ApprovalGate, CLI: `setup`, `profile`, `run`, `status`, `pause`, `export`)

## 3. Key Guardrails & Non-Negotiable Invariants
- **Truth Invariants**: Grounding check required for all generated content. Meaning may be tailored, facts CANNOT be manufactured or hallucinated. Contradictions trigger reconciliation.
- **Action Invariants**: Default site trust starts at `supervised`. Every external mutation requires an effect identity / idempotency key. Banned/restricted accounts trigger automatic circuit breakers.
- **Security Invariants**: Zero secrets in git/logs. PII encrypted at rest using `age` and OS keyring. Database isolated to `0600` permissions. Loopback-only API with token auth.
- **Legal & Stealth**: Stealth active by default (Patchright/Camoufox, rate jittering). Auto-registration disabled for unsafe sites; registration assistance with conservative pauses for consent/CAPTCHA/terms.

## 4. Current Runtime Constraints
- **Target OS**: Windows (primary development target), Linux (release requirement), cross-platform Python core.
- **Licensing**: AGPL-3.0-only for core system; MIT for site adapters.
- **Telemetry**: Disabled by default (opt-in only with strict data exclusion).
