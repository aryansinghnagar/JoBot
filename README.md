# `jobot` — Autonomous Job Application Operating System

Local-First, Privacy-Preserving, Human-Governed Job Discovery and Application Assistance.

## Overview
`jobot` is an agentic operating system designed to automate job application workflows. The system is undergoing an active refactor per `JoBot_Refactor_Plan.md` from a stub skeleton into a release-ready production engine.

## Architecture
- **CLI**: Built with `typer` and `rich`
- **Core Engine**: Python 3.11+ async execution fabric & task graph engine
- **Browser Stack**: Patchright (stealth Playwright fork) integration in progress
- **Security & Storage**: SQLite WAL control plane + Fernet encryption + OS Keyring
- **AI Routing**: Provider-neutral `ModelRouter` (Gemini, OpenAI, Anthropic, Ollama fallbacks)

## Refactor Progress
- Currently refactoring core architecture per `JoBot_Refactor_Plan.md`.
- See `worklog.md` for real-time task execution logs.

## License
- Core system: GNU AGPL v3.0 (`AGPL-3.0-only`)
- Site adapters: MIT License
