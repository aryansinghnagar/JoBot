# JoBot Documentation Index

## Authoritative Plan (current)

The **JoBot Merge Plan** (Draft 1.0, August 2026) is the current authoritative
specification. It is an architectural blueprint for merging the best
functionality of 33 open-source job-search AI repositories into `jobot`.

- [`plan.md`](../plan.md) — markdown companion (executive summary, decisions, roadmap)
- [`JoBot_Merge_Plan.pdf`](../JoBot_Merge_Plan.pdf) — full 127-page version
- [`SETUP.md`](../SETUP.md) — setup, configuration & secrets, Docker, CLI reference, troubleshooting
- [`repo_research.md`](../repo_research.md) — the research artifact behind the plan (Task R-1; 33 repos, GitHub-API-verified star counts on 2026-08-13). Its "JoBot Current State" section is a snapshot taken before Phase 0 — where it differs from code, code is truth
- [`cover.html`](../cover.html) — HTML source of the `JoBot_Merge_Plan.pdf` cover (pdf.py toolchain)

## Phase 0 Deliverables

- [`asp.md`](asp.md) — the 12-phase Application Submission Pipeline (ASP), single source of truth
- [`contracts.md`](contracts.md) — frozen public interfaces the merge must not break (includes the Phase 1 addendum on `jobot/llm/`, the Phase 2 addendum on `jobot/scrapers/`, and the Phase 3 addendum on `jobot/documents/` + `jobot/asp/`)

## Phase 1 Deliverables

Provider abstraction + config layer (plan.md Chapter 6):

- [`jobot/llm/`](../src/jobot/llm/) — `ModelRouter` v2 (cost-aware, spend persisted to `~/.jobot/data/llm_spend.json`), 12-entry `PROVIDER_REGISTRY`, `pricing.yaml`, provider ABC
- [`jobot/secrets.py`](../src/jobot/secrets.py) — OS keyring wrapper (service `jobot`)
- [`jobot/config/`](../src/jobot/config/) — three-tier `ConfigManager` (env → keyring → `~/.jobot/config.yaml`) + profiles YAML loader (config-only, identity stays in the Fernet vault)
- CLI: `jobot config get/set/unset/show`, `jobot doctor`
- Live provider tests opt-in: `JOBOT_RUN_LIVE_LLM=1 pytest tests/integration/test_llm_providers_live.py`

## Phase 2 Deliverables

Scraper merge (plan.md Chapter 12 + §316–325): real feeds only, no fabricated data:

- [`jobot/scrapers/`](../src/jobot/scrapers/) — `JobSpyAdapter` (8 boards, `python-jobspy` via `--no-deps` recipe), direct-API ATS families (lever/ashby/smartrecruiters), `CareerPageScanner` + verified `career_sites.yaml` starter set, two-tier `DedupService` (exact hash + vector cosine ≥ 0.92, persisted `job_dedup_cache` table)
- [`jobot/discovery/engine.py`](../src/jobot/discovery/engine.py) — discovery against real feeds only; unscrapable boards skipped
- [`jobot/adapters/greenhouse.py`](../src/jobot/adapters/greenhouse.py) — fabrication removed (parse raises on fetch error; honest `discover_jobs`)
- CLI: `jobot scrape <board> [--keywords --location --limit --companies --all --json --no-dedup]`, `jobot dedup [--stats]`
- Config keys: `scraper.jobspy.delay_s`, `scraper.jobspy.proxy_list`
- Live scraper tests opt-in: `JOBOT_RUN_LIVE_SCRAPE=1 pytest tests/integration/test_scrape_live.py`

## Phase 3 Deliverables

Document stack + auto-apply orchestration (plan.md §327–339):

- [`jobot/documents/`](../src/jobot/documents/) — LaTeX templates (`default`/`modern`/`classic`), `TailorLoop` (drafter→reviewer, ≤3 iterations), deterministic grounding gate (`verify_fact_truthfulness_detailed`), 5-tone cover letters, pluggable PDF engines (LuaLaTeX + pure-python reportlab fallback), `AtsScorer` (≥ 0.85 threshold)
- [`jobot/asp/`](../src/jobot/asp/) — `saga.py` (apply saga over new `saga_instances`/`saga_steps` tables) + `orchestrator.py` (tailor → gate → artifacts → 12-phase pipeline; supervised approval gate, compensation, dry-run)
- [`jobot/stealth/linkedin_easy_apply.py`](../src/jobot/stealth/linkedin_easy_apply.py) — Easy Apply saga (selector-driven; hermetic Flask harness in `tests/mock_linkedin/`)
- Adapters: `lever.py` real API (parse + submit + confirmation capture), `greenhouse.py` resume `content_base64`, `linkedin.py` honest `NotImplementedError` (no fabrication)
- CLI: `jobot apply <job-id|--url> [--dry-run --approve --resume --template --tone --engine]`, `jobot coverletter`, `jobot qa`, `jobot resume {runner|tailor|ats-check|templates}`, `jobot scrape --save`
- Live browser tests opt-in: `JOBOT_RUN_LIVE_BROWSER=1 pytest tests/integration/test_linkedin_easy_apply_live.py`

## Existing

- [`dev/architecture.md`](dev/architecture.md) — core architecture notes
- [`user/cli-reference.md`](user/cli-reference.md) — user-facing CLI reference

## Historical (superseded planning docs)

Moved here during Phase 0 audit/cleanup (see `worklog.md`); kept for reference
only. Do not treat as authoritative:

- `history/agent.md` — architect doctrine prompt
- `history/unified_master_plan.md` — pre-merge merged master plan (~41k lines)
- `history/job_application_automaton_plan.md` — Source B of the old master plan
- `history/plan_source_A.md` — old `plan.md` (Source A of the old master plan)
- `history/operating_summary.md` — stale in places (e.g., claims `age` encryption; code uses Fernet — see `AGENTS.md`)
- `history/runtime_capability_matrix.md`
- `history/JoBot_Refactor_Plan.md` + `history/JoBot_Refactor_Review_2.md` — refactor plan/review (superseded by the merge plan)
- `history/implementation_contract_*.md` — dev/release contracts
- `history/Improvement_Plan.txt`, `history/base_prompt.txt`