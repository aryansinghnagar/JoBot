# `jobot` — Autonomous Job Application Operating System

Local-First, Privacy-Preserving, Human-Governed Job Discovery and Application Assistance.

## Overview
`jobot` is a self-improving agentic operating system designed to automate repetitive job application workflows across 25+ job portals and Applicant Tracking Systems (ATS), with India as the primary market and global portals supported.

## Architecture
- **CLI**: Built with `typer` and `rich`
- **Core Engine**: Python 3.11+ async execution fabric & task graph engine
- **Browser Stack**: `patchright` (stealth Playwright fork) & `camoufox`
- **Security & Storage**: SQLite WAL control plane + `age` encryption + OS Keyring
- **AI Routing**: Provider-neutral `ModelRouter` (Gemini, OpenAI, Anthropic, Ollama)

## License
- Core system: GNU AGPL v3.0 (`AGPL-3.0-only`)
- Site adapters: MIT License
