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
- [`contracts.md`](contracts.md) — frozen public interfaces the merge must not break

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