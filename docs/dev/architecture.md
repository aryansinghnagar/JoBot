# JoBot System Architecture & Layered Design

`jobot` is built according to a local-first, privacy-preserving 12-Layer System Architecture.

## Architectural Layers

- **Layer 1 (Identity & Data Grounding)**: Candidate `profile.yaml` canonical source of truth stored encrypted in `~/.jobot/profiles/`. Zero hallucinated facts permitted.
- **Layer 2 (Security & Cryptography)**: Deterministic secret management using `age` encryption and OS keyring.
- **Layer 3 (Storage & Persistence)**: SQLite database (`~/.jobot/jobot.db`) storing job postings and application records with strict foreign key constraints and `idempotency_key` deduplication.
- **Layer 4 (Discovery & Match Engine)**: Multi-portal job discovery and `SkillExtractor` matching candidate fit scores against requisitions.
- **Layer 5 (Adapter Layer)**: Modular portal adapters inheriting `SiteAdapter` base class (`NaukriAdapter`, `GreenhouseAdapter`, `MockATSAdapter`, etc.).
- **Layer 6 (Q&A & Grounding Engine)**: `QAEngine` answering custom application questions strictly grounded in profile facts with sensitive field detection.
- **Layer 7 (Policy Engine)**: Policy enforcement checking daily per-portal submission limits, company exclusions, and compensation rules.
- **Layer 8 (Stealth & Behavioral Mimicry)**: `BrowserSession` Patchright persistent browser automation, 4-point cubic Bezier mouse curve generation, and LLM vision CAPTCHA solving.
- **Layer 9 (12-Phase ASP Pipeline)**: `ApplicationSubmissionPipeline` executing 12 distinct ASP phases (`PHASE_1_INTENT` to `PHASE_12_VERIFY`) with strict per-phase Definition of Done (DoD) verification gates.
- **Layer 10 (Observability & Tracing)**: OpenTelemetry-compatible `TraceLogger` JSONL span persistence and `AlertDispatcher` operational notifications.
- **Layer 11 (Evaluation Harness)**: `EvalHarness` running continuous benchmark scenarios across 6 core categories.
- **Layer 12 (Interface & CLI)**: Rich-rendered Typer CLI application (`jobot`).
