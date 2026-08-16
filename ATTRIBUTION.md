# JoBot — Attribution, References & Open Source Licenses

This document provides complete, transparent attribution and citations for all open-source repositories, libraries, design patterns, and research that inspired the architecture of **JoBot**.

JoBot is developed with a strict **Clean-Room Implementation & Zero-Plagiarism Policy**. All core orchestration code, durable state machines, security guards, grounding verifiers, and ATS adapters in `src/jobot/` are original works licensed under the **GNU Affero General Public License v3.0 (`AGPL-3.0-only`)**, with site adapters available under the **MIT License**.

---

## 1. Architectural Inspirations & Research Citations

The design of JoBot synthesizes best-in-class concepts from open-source job automation utilities, agentic operating system architectures, and academic research in reliable LLM application development:

### A. Job Aggregation & ATS Scraping Patterns
1. **JobSpy** (`cullenwatson/JobSpy`)
   - *License*: MIT License
   - *Repository*: `https://github.com/cullenwatson/JobSpy`
   - *Inspiration*: Inspiration for multi-board job board querying parameters, pagination handling, and deduplication hashing concepts. JoBot implements its own clean-room async discovery engine with SSRF-guarded HTTP clients and direct API adapters.

2. **JobFunnel** (`PaulMcInnis/JobFunnel`)
   - *License*: BSD 3-Clause License
   - *Repository*: `https://github.com/PaulMcInnis/JobFunnel`
   - *Inspiration*: Local-first SQLite application tracking, status transitions, and automated daily email digest concepts.

### B. Browser Automation & Form-Filling State Machines
3. **LinkedIn_AIHawk / Auto_Jobs_Applier_AI_Agent** (`federici-m/LinkedIn_AIHawk`)
   - *License*: MIT License
   - *Repository*: `https://github.com/federici-m/LinkedIn_AIHawk`
   - *Inspiration*: Multi-step modal navigation concepts for LinkedIn Easy Apply. JoBot clean-room engineered a deterministic saga orchestrator (`LinkedInEasyApplySaga`) with strict human-in-the-loop approval gates, self-healing selectors (`SelectorRegistry`), and non-repudiation DOM evidence hashing (`BrowserEvidenceCollector`).

4. **linkedIn-easy-apply-bot** (`nicolasfguerrero/linkedIn-easy-apply-bot`) & **EasyApplyJobsBot** (`mstephen19/EasyApplyJobsBot`)
   - *License*: MIT License
   - *Inspiration*: Unanswered question handling, radio button heuristic mapping, and modal error recovery strategies.

### C. Resume Formatting & Ingestion
5. **Reactive-Resume** (`AmruthPillai/Reactive-Resume`) & **OpenResume** (`xitanggg/open-resume`)
   - *License*: MIT License
   - *Inspiration*: Structured JSON-to-PDF typography design, ATS-friendly single-column layout principles, and keyword density scoring models.

6. **pdfminer.six** (`pdfminer/pdfminer.six`)
   - *License*: MIT License
   - *Repository*: `https://github.com/pdfminer/pdfminer.six`
   - *Inspiration*: Robust, pure-Python PDF layout extraction utilized in JoBot's `ResumeImporter`.

### D. Agentic Reliability & Distributed Systems Patterns
7. **Saga Execution Pattern & Outbox Reliability** (Hector Garcia-Molina & Kenneth Salem, 1987)
   - *Reference*: *Sagas*, ACM SIGMOD Record, Vol. 16, Issue 3.
   - *Application in JoBot*: Forward execution with compensating undo actions across multi-step browser workflows in `ApplySaga` and `DurableTaskEngine`.

8. **Self-Reflective LLM Revision Loops (Reflexion / Drafter-Reviewer)** (Shinn et al., 2023)
   - *Reference*: *Reflexion: Language Agents with Active Reinforcement Learning*, NeurIPS 2023.
   - *Application in JoBot*: Two-pass Drafter-Reviewer architecture in `DocumentTailor` enforcing rubric-based evaluations and truth grounding before human presentation.

---

## 2. Third-Party Runtime Dependencies & Licenses

JoBot relies on the following open-source libraries. None of their terms are violated, and all are compatible with GNU AGPL v3.0 / MIT licensing:

| Dependency | Upstream Project | License | Purpose in JoBot |
| :--- | :--- | :--- | :--- |
| **`pydantic`** | [pydantic/pydantic](https://github.com/pydantic/pydantic) | MIT | Type validation, domain models, settings schemas |
| **`typer`** / **`click`** | [fastapi/typer](https://github.com/fastapi/typer) | MIT | Command-line interface parsing and command routing |
| **`rich`** | [Textualize/rich](https://github.com/Textualize/rich) | MIT | Terminal formatting, progress indicators, tables |
| **`cryptography`** | [pyca/cryptography](https://github.com/pyca/cryptography) | Apache-2.0 / BSD | AES-128-CBC / Fernet symmetric profile encryption |
| **`keyring`** | [jaraco/keyring](https://github.com/jaraco/keyring) | MIT | OS-level credential vault integration (DPAPI/SecretService/Keychain) |
| **`patchright`** / **`playwright`** | [kaliiiiiiiiii/patchright](https://github.com/kaliiiiiiiiii/patchright) | Apache-2.0 | Stealth browser automation and DOM snapshot capture |
| **`google-genai`** | [googleapis/python-genai](https://github.com/googleapis/python-genai) | Apache-2.0 | Google Gemini API integration |
| **`jinja2`** | [pallets/jinja](https://github.com/pallets/jinja) | BSD-3-Clause | Cover letter and resume template rendering |
| **`reportlab`** | [reportlab.com](https://www.reportlab.com/) | BSD-3-Clause | Vector PDF generation and formatting |
| **`pdfminer.six`** | [pdfminer/pdfminer.six](https://github.com/pdfminer/pdfminer.six) | MIT | Resume PDF text extraction and structural analysis |
| **`pyyaml`** | [yaml/pyyaml](https://github.com/yaml/pyyaml) | MIT | Structured configuration and prompt presets |
| **`tauri`** | [tauri-apps/tauri](https://github.com/tauri-apps/tauri) | Apache-2.0 / MIT | Lightweight desktop shell and OS window management |
| **`react`** / **`react-dom`** | [facebook/react](https://github.com/facebook/react) | MIT | Desktop GUI reactive component framework |
| **`vite`** / **`vitest`** | [vitejs/vite](https://github.com/vitejs/vite) | MIT | Frontend bundle pipeline and unit test runner |

---

## 3. License Compatibility & Clean-Room Statement

1. **Clean-Room Engineering**: No copyrighted code, proprietary algorithms, or closed-source scrapers have been copied into this repository. All parsers, state machines, and adapters were written from scratch using public HTTP endpoint contracts and semantic HTML analysis.
2. **Copyleft & Permissive Balance**: The core JoBot orchestrator and state engine are licensed under **AGPL-3.0-only**, ensuring that any network-deployed or distributed enhancements remain free and open. Site adapters are licensed under the **MIT License** to facilitate community contribution without restrictive barriers.
3. **Trademark Notice**: All product names, logos, brands, and registered trademarks (e.g., LinkedIn, Greenhouse, Lever, Workday, Ashby, Workable, Recruitee, Teamtailor, BambooHR, Naukri) are property of their respective owners. Their mention in JoBot is solely for descriptive compatibility and interoperability purposes under nominative fair use.
