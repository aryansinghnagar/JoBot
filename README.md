# `jobot` — Autonomous Job Application Operating System

> **Local-First, Privacy-Preserving, Human-Governed Job Discovery and Application Engine.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/Tests-667%20passed-success.svg)](tests/)

---

## Overview

`jobot` is an agentic operating system designed to automate end-to-end job discovery, resume tailoring, and multi-portal application workflows with strict non-repudiation evidence logging, zero-hallucination candidate truth verification, and durable human-in-the-loop governance.

The authoritative specification is **[`docs/dev/master-plan.md`](file:///c:/Users/Aryan/OneDrive/Desktop/Coding%20Projects/4-JobAppAgent/docs/dev/master-plan.md)** (with technical architecture in **[`docs/dev/architecture.md`](file:///c:/Users/Aryan/OneDrive/Desktop/Coding%20Projects/4-JobAppAgent/docs/dev/architecture.md)**).

---

## Core Capabilities

- **Durable Task Engine & Idempotency (`DurableTaskEngine`)**: Atomic SQLite lease claims (`BEGIN IMMEDIATE`), heartbeats, and external effect reservation preventing double-submitting across process restarts or crashes.
- **AI Reliability & Candidate Truth System (`CandidateTruthStore`)**: Two-pass Drafter-Reviewer rubric loop with independent A–F scoring and automated claim verification ensuring zero fabricated credentials or metrics.
- **4-Stage Matching Ladder (`MatchingLadder`)**: Progresses from hard filters (location/experience) to skill overlap (Jaccard), bigram cosine similarity, and structured LLM fit explanations.
- **Browser Automation & Non-Repudiation (`BrowserEvidenceCollector`)**: Stealth session management (`Patchright`), self-healing selector fallback chains (`SelectorRegistry`), and pre/post DOM HTML and screenshot SHA256 hashing in `manifest.json`.
- **Direct ATS & CXS Adapters**: Full native support for Greenhouse, Lever, Workday, Ashby, Workable, Recruitee, Teamtailor, BambooHR, Naukri, and LinkedIn Easy Apply modal sagas.
- **Desktop Cockpit & Human Approval Inbox**: Tauri 2 + React desktop interface featuring real-time Approval Inboxes, Evidence Viewers, and live ATS Site Health circuit breaker monitoring.

---

## Attribution & Intellectual Integrity

`jobot` is engineered under a strict **Clean-Room Implementation & Zero-Plagiarism Policy**. All core orchestration code, algorithms, state machines, and adapters are original works.

For full academic citations, design pattern references, and third-party open-source license notices (including `JobSpy`, `JobFunnel`, `LinkedIn_AIHawk`, `Reactive-Resume`, and upstream libraries), see **[`ATTRIBUTION.md`](file:///c:/Users/Aryan/OneDrive/Desktop/Coding%20Projects/4-JobAppAgent/ATTRIBUTION.md)**.

---

## License

- **Core System & Orchestrator**: GNU Affero General Public License v3.0 ([`AGPL-3.0-only`](file:///c:/Users/Aryan/OneDrive/Desktop/Coding%20Projects/4-JobAppAgent/LICENSE))
- **Site Adapters**: [MIT License](https://opensource.org/licenses/MIT)

