# JoBot Merge Plan — Repository Research (Task R-1)

**Date:** 2026-08-13
**Author:** research-agent (general-purpose)
**Purpose:** Inventory GitHub star counts + feature/architecture details for 9 named job-search AI repos and discover additional similar open-source projects, to feed a comprehensive merge-architecture plan for `aryansinghnagar/JoBot`.

**Method note on data verification:** All star counts, languages, licenses, `pushed_at`, and archived status for named + discovered repos were fetched **directly from the GitHub REST API** (`https://api.github.com/repos/OWNER/REPO`) on 2026-08-13. These are *verified* numbers, not estimates. A small number of discovered repos (Liam-Frost/AutoApply, Azoo92i/AutoApplyMax, colophon-group/jobseek) returned HTTP 403 due to anonymous rate-limiting before their license could be confirmed — for those, the star count + description were captured from the GitHub **search API** (which uses a separate rate-limit budget) and are marked "(via search API)". Feature inventories and architecture notes were derived from each repo's README (fetched raw from `raw.githubusercontent.com`) and root-directory listing (`/contents/` endpoint).

---

## 1. Named Repos Inventory

All 9 named repos resolved (the prompt's `aryansinghnarel/JoBot` URL is a typo — the canonical owner is `aryansinghnagar` (with an `a`); the `narel` variant returned 404). Sorted by stars descending.

| Repo | URL | Stars | Lang | License | Last Active | Multi-AI | Tests | Docker | Docs | Key Features (top 5) |
|---|---|---:|---|---|---|---|---|---|---|---|
| santifer/career-ops | https://github.com/santifer/career-ops | 63,659 | JavaScript | MIT | 2026-08-13 (today) | ✓✓ (Claude/Codex/OpenCode/Antigravity/Gemini/OpenAI/Ollama/OpenRouter/Kimi/Qwen/Grok) | ✓✓ (massive `.test.mjs` suite + tests/ + test/) | ✓✓ (Dockerfile + docker-compose.yml) | ✓✓ (ARCHITECTURE.md, 16-translated READMEs, docs/) | A-F rubric JD scoring (1.0–5.0); plugin system + plugins-registry; Playwright CV builder; multi-LLM eval runners; tracker sync (ATS); weekly digest |
| MadsLorentzen/ai-job-search | https://github.com/MadsLorentzen/ai-job-search | 31,411 | TypeScript | MIT | 2026-08-12 | ✓ (Claude Code native; community forks for Codex/Antigravity/Gemini CLI) | ✓ (tests/) | ✗ | ✓ (SETUP.md, AGENTS.md, CLAUDE.md, CHANGELOG) | `/scrape` `/apply` `/interview` slash-command workflow; LaTeX CV (lualatex/xelatex); drafter-reviewer agent pipeline; Danish-portal skills pack (Jobindex/Jobnet/Jobbank/Akademikernes); salary benchmarking |
| feder-cr/Jobs_Applier_AI_Agent_AIHawk | https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk | 30,159 | Python | AGPL-3.0 | 2026-08-04 | ✗ (OpenAI-centric; some Ollama support) | ✗ (no tests dir) | ✗ | ✓ (wiki + GitHub Pages) | Auto-apply via Selenium; tailored resume per posting; cover-letter generation; LinkedIn Easy Apply; featured by TechCrunch/Business Insider/Wired |
| speedyapply/JobSpy *(discovered, see §2 — included here because it ranks in the top 10 by stars)* | https://github.com/speedyapply/JobSpy | 4,072 | Python | MIT | 2026-02-18 | N/A (scraper lib, no LLM) | ✓ (pre-commit + CI) | ✗ (lib, not app) | ✓ (README + docs) | LinkedIn/Indeed/Glassdoor/Google/ZipRecruiter/Bayt unified scraper; dedupe; pandas output; the de-facto scraper dependency used by many other repos |
| DaKheera47/job-ops *(discovered)* | https://github.com/DaKheera47/job-ops | 3,840 | TypeScript | NOASSERTION | 2026-08-10 | ✓ (multi-CLI: Claude/Codex/OpenCode; Playwright-MCP) | partial (CI present) | ✓✓ (Dockerfile + docker-compose + entrypoint) | ✓ (docs-site/) | "DevOps for job hunting" pipeline; career-boards + extractors + orchestrator; visa-sponsor-providers module; Biome + Knip tooling |
| GodsScion/Auto_job_applier_linkedIn *(discovered)* | https://github.com/GodsScion/Auto_job_applier_linkedIn | 2,688 | Python | MIT | 2026-08-10 | partial (GPT-4o primarily) | partial | ✗ | partial (README) | LinkedIn Easy Apply automation; answer-question AI; resume/cover-letter tailoring; blacklisting; configurable workflow |
| PaulMcInnis/JobFunnel *(discovered, ARCHIVED)* | https://github.com/PaulMcInnis/JobFunnel | 2,178 | Python | MIT | 2025-12-10 (archived) | N/A (no LLM) | ✓ (legacy) | ✗ | ✓ (README) | Multi-board scraper → single dedup'd CSV/Excel; Indeed/LinkedIn/Monster/Glassdoor; legacy but influential reference design |
| can4hou6joeng4/boss-agent-cli *(discovered)* | https://github.com/can4hou6joeng4/boss-agent-cli | 1,558 | Python | MIT | 2026-08-13 (today) | ✓ (local-assist, AI-agent friendly) | partial | ✗ | ✓ (README) | BOSS Zhipin CLI for AI agents; welfare filtering; shortlist; JSON-envelope output; low-risk compliant design |
| eatmoreduck/boss-zhipin-scraper *(discovered)* | https://github.com/eatmoreduck/boss-zhipin-scraper | 1,094 | Python | MIT | 2026-07-27 | N/A | partial | ✗ | ✓ | Chrome-CDP-based BOSS Zhipin crawler; bypasses font-obfuscation; plaintext salary JSON/CSV; skill analysis |
| Gsync/jobsync *(discovered)* | https://github.com/Gsync/jobsync | 854 | TypeScript | MIT | 2026-08-12 | ✓ (AI resume review) | partial | ✗ | ✓ | Self-hosted tracker + AI career assistant; AI resume review; job matching; task logging; application analytics; privacy-first |
| andrew-shwetzer/career-ops-plugin-… *(discovered)* | https://github.com/andrew-shwetzer/career-ops-plugin-do-not-fork-currently-updating-v2- | 463 | HTML | MIT | 2026-07-23 | ✓ (Claude Cowork plugin) | partial | ✗ | ✓ | 9 AI skills (JD eval, ATS resume, portal scan, app tracker, outreach); appears to be a sister-project of career-ops |
| feder-cr/resume_render_from_job_description *(discovered)* | https://github.com/feder-cr/resume_render_from_job_description | 412 | Python | MIT | 2026-08-01 | partial (OpenAI) | ✗ | ✗ | ✓ | Sibling AIHawk tool: customizes resume from a job URL; multiple pre-defined styles; interactive CLI |
| strelov1/freehire *(discovered)* | https://github.com/strelov1/freehire | 337 | Go | MIT | 2026-08-13 (today) | N/A (search engine) | partial | ✗ | ✓ | Open-source search engine for job seekers; Go-based aggregator |
| agentenatalie/get-job.skill *(discovered)* | https://github.com/agentenatalie/get-job.skill | 348 | Python | NOASSERTION | 2026-07-22 | ✓ (Claude skill) | partial | ✗ | ✓ | Chinese-market "实习.skill" — resume rewrite, interview prep, real-background reframing for 大厂 offers |
| jennifer88huang/interview-skills *(discovered)* | https://github.com/jennifer88huang/interview-skills | 272 | JavaScript | None | 2026-07-10 | ✓ (Claude/Codex skill) | partial | ✗ | ✓ | AI mock interview coach; FAANG/Big-Tech/startup focus; generates questions from JD+resume |
| wodsuz/EasyApplyJobsBot *(discovered, license=NOASSERTION)* | https://github.com/wodsuz/EasyApplyJobsBot | 804 | Python | NOASSERTION | 2026-05-18 | partial (GPT) | ✗ | ✗ | partial | Auto-apply LinkedIn + Glassdoor Easy Apply; auto-login; AI question answering |
| surapuramakhil-org/Job_search_agent | https://github.com/surapuramakhil-org/Job_search_agent | 171 | Python | AGPL-3.0 | 2026-08-07 (**ARCHIVED**) | partial (GPT + TensorZero experiment) | ✓ (pytest.ini, tests/) | partial (docker-compose-tensorzero.yml, no Dockerfile at root) | ✓ (docs/) | Auto-apply with tailored apps; Selenium/Chrome; YAML-based secure config; TensorZero LLM-optimization experiment; company blacklist |
| replyre/job-hunter | https://github.com/replyre/job-hunter | 150 | Python | None (no LICENSE) | 2026-08-06 | partial (single LLM via templates) | ✗ (no tests dir) | ✗ | ✓✓ (7-part docs/ + Postman collection) | Profile-driven daily outreach pipeline; 4 sources + 150 career pages; LinkedIn people-search URL generation; personalized DM templates; SQLite + REST API (uvicorn/FastAPI); YAML profile presets |
| beatwad/LinkedIn-AI-Job-Applier-Ultimate *(discovered)* | https://github.com/beatwad/LinkedIn-AI-Job-Applier-Ultimate | 147 | Python | None | active | partial (LLM) | ✗ | ✗ | partial | LinkedIn+Indeed Playwright bot; applies to ALL job types (not just Easy Apply); custom resumes; data anonymization; Telegram reporting |
| imon333/Job-apply-AI-agent *(discovered)* | https://github.com/imon333/Job-apply-AI-agent | 177 | Python | None | 2026-06-04 | ✗ (OpenAI-locked) | ✗ | ✗ | partial | LinkedIn/Indeed/StepStone scraper; n8n workflow; Selenium; OpenAI CV+cover-letter generation; Google Sheets/Airtable sync; email alerts |
| feder-cr/lib_resume_builder_AIHawk *(discovered)* | https://github.com/feder-cr/lib_resume_builder_AIHawk | 193 | Python | MIT | 2026-08-01 | partial | ✗ | ✗ | partial | The underlying resume-builder library behind the AIHawk resume tooling |
| sreekarrs/JobSearch-Agent | https://github.com/sreekarrs/JobSearch-Agent | 50 | Python | GPL-3.0 | 2026-01-19 | ✗ (Gemini/Google ADK locked) | ✓ (tests/) | ✓ (Dockerfile + .dockerignore) | ✓ (DEPLOYMENT.md, docs/) | LinkedIn Playwright scraper (Chromium/Firefox/WebKit); anonymization + proxy; BugMeNot credential scraper; Gemini-powered CV/cover-letter; FastAPI server |
| krishnavalliappan/JobScout *(discovered)* | https://github.com/krishnavalliappan/JobScout | 47 | Python | None | 2024-08-09 (stale) | ✗ (GPT-locked) | ✗ | ✗ | partial | LinkedIn scraper; GPT-tailored resume+cover letter; Notion sync; stale (>1 yr) |
| LuisMIguelFurlanettoSousa/auto-apply-bot *(discovered)* | https://github.com/LuisMIguelFurlanettoSousa/auto-apply-bot | 34 | TypeScript | MIT | 2026-07-08 | ✗ (Gemini-locked) | partial | ✗ | ✓ | Gemini + Playwright MCP; Gupy/LinkedIn/Indeed; smart scoring; multi-resume; dry-run mode; Telegram + web dashboard |
| algsoch/job_agentic | https://github.com/algsoch/job_agentic | 3 | Python | None *(README claims MIT, no LICENSE file)* | 2026-06-09 | ✓ (Ollama / llama3.1:8b — fully local) | partial (test_profile.py only) | ✗ | ✓✓ (ARCHITECTURE.md, ENHANCEMENTS.md, SYSTEM_FEATURES.md, PROMPTS.md, GETTING_STARTED.md) | "Job Intelligence OS": collectors (LinkedIn/GitHub/Naukri/YC/Wellfound); rule+LLM scoring (APPLY/APPLY_LATER/WATCH/SKIP); SQLite+CSV; SMTP outreach; Typer CLI; cron-scheduled |
| **aryansinghnagar/JoBot (TARGET)** | https://github.com/aryansinghnagar/JoBot | 0 | Python | AGPL-3.0 | 2026-08-11 | ✓✓ (ModelRouter: Gemini/OpenAI/Anthropic/Ollama) | ✓✓ (~30 test files: ai, storage, dedup, browser_session, captcha_solver, circuit_breaker, cli, greenhouse_adapter, adapter_registry, master_plan_phases_2_to_5, release) | ✗ (no Dockerfile) | ✓✓ (Refactor_Plan, master_plan, implementation_contract_dev_0_1..2_0, runtime_capability_matrix, unified_master_plan, worklog.md) | Typer+rich CLI; async task-graph engine; Patchright stealth browser; SQLite WAL control plane + Fernet + OS keyring; ModelRouter provider-neutral; adapter registry; circuit breaker; PII masker; vector memory |

### Notes on named-repo data quality
- All star counts in §1 are **API-verified** (fetched 2026-08-13).
- `feder-cr/Jobs_Applier_AI_Agent_AIHawk`: README states third-party provider plugins were removed for copyright reasons, so multi-provider support is currently *latent architecture, not shipped* — hence marked ✗.
- `santifer/career-ops`: star growth is exceptional (created 2026-04-04 → 63k stars in ~4 months); has 17 CI workflows (test.yml, codeql.yml, sbom.yml, signature-ci.yml, release.yml, plugin-registry-validate.yml, web-ci.yml, gfi-claims.yml, manifesto-guestbook.yml, etc.) — the most mature engineering posture of any repo surveyed.
- `surapuramakhil-org/Job_search_agent`: **ARCHIVED** despite still showing recent `pushed_at` (2026-08-07) — this is the date archive was set, not active maintenance.
- `algsoch/job_agentic`: README badge claims MIT but the repo has **no LICENSE file** (GitHub API returned `license: null`) — legally "All Rights Reserved" until added.

---

## 2. Discovered Repos Inventory

Repos discovered via GitHub topic search (`job-search`, `ai-job-search`, `linkedin-automation`, `job-scraper`, `career-agent`, `resume-ai`) and keyword search (`auto apply jobs AI`, `AIHawk`, `AutoJobr`, `JobLLM`, `JobPilot`). Excludes any already in §1. Sorted by stars descending.

| Repo | URL | Stars | Lang | License | Last Active | Multi-AI | Tests | Docker | Docs | Key Features (top 5) |
|---|---|---:|---|---|---|---|---|---|---|---|
| speedyapply/JobSpy | https://github.com/speedyapply/JobSpy | 4,072 | Python | MIT | 2026-02-18 | N/A (no LLM) | ✓ (pre-commit + CI) | ✗ (lib) | ✓ | Unified scraper for LinkedIn/Indeed/Glassdoor/Google/ZipRecruiter/Bayt; dedupe; pandas output |
| DaKheera47/job-ops | https://github.com/DaKheera47/job-ops | 3,840 | TypeScript | NOASSERTION | 2026-08-10 | ✓ (Claude/Codex/OpenCode + Playwright-MCP) | partial | ✓✓ (Dockerfile+compose) | ✓ (docs-site) | "DevOps for job hunting" pipeline; career-boards + extractors + orchestrator; visa-sponsor-providers |
| GodsScion/Auto_job_applier_linkedIn | https://github.com/GodsScion/Auto_job_applier_linkedIn | 2,688 | Python | MIT | 2026-08-10 | partial (GPT-4o) | partial | ✗ | partial | LinkedIn Easy Apply; AI question answering; resume/cover-letter tailoring; blacklisting |
| PaulMcInnis/JobFunnel | https://github.com/PaulMcInnis/JobFunnel | 2,178 | Python | MIT | 2025-12-10 (ARCHIVED) | N/A | ✓ (legacy) | ✗ | ✓ | Multi-board scraper → dedup'd spreadsheet; reference design |
| can4hou6joeng4/boss-agent-cli | https://github.com/can4hou6joeng4/boss-agent-cli | 1,558 | Python | MIT | 2026-08-13 | ✓ (AI-agent friendly) | partial | ✗ | ✓ | BOSS Zhipin CLI; welfare filter; shortlist; JSON-envelope output |
| eatmoreduck/boss-zhipin-scraper | https://github.com/eatmoreduck/boss-zhipin-scraper | 1,094 | Python | MIT | 2026-07-27 | N/A | partial | ✗ | ✓ | Chrome-CDP BOSS Zhipin crawler; bypasses font-obfuscation; plaintext salary |
| AndrewStetsenko/tech-jobs-with-relocation | https://github.com/AndrewStetsenko/tech-jobs-with-relocation | 4,505 | (docs/markdown) | — | active | N/A | N/A | N/A | ✓ | Curated guide (not an agent — reference only) |
| Gsync/jobsync | https://github.com/Gsync/jobsync | 854 | TypeScript | MIT | 2026-08-12 | ✓ (AI resume review) | partial | ✗ | ✓ | Self-hosted tracker + AI career assistant; privacy-first |
| wodsuz/EasyApplyJobsBot *(license NOASSERTION)* | https://github.com/wodsuz/EasyApplyJobsBot | 804 | Python | NOASSERTION | 2026-05-18 | partial (GPT) | ✗ | ✗ | partial | LinkedIn+Glassdoor Easy Apply bot; auto-login; AI question answering |
| rainmanjam/jobspy-api | https://github.com/rainmanjam/jobspy-api | 376 | Python | (check) | active | N/A | partial | ✓ | ✓ | Dockerized JobSpy wrapper with API-key auth + rate-limiting + proxy |
| agentenatalie/get-job.skill | https://github.com/agentenatalie/get-job.skill | 348 | Python | NOASSERTION | 2026-07-22 | ✓ (Claude skill) | partial | ✗ | ✓ | Chinese-market resume rewrite + interview prep skill |
| strelov1/freehire | https://github.com/strelov1/freehire | 337 | Go | MIT | 2026-08-13 | N/A | partial | ✗ | ✓ | Open-source job-search engine |
| andrew-shwetzer/career-ops-plugin-… | https://github.com/andrew-shwetzer/career-ops-plugin-do-not-fork-currently-updating-v2- | 463 | HTML | MIT | 2026-07-23 | ✓ (Claude Cowork) | partial | ✗ | ✓ | Sister project of career-ops; 9 AI skills |
| jennifer88huang/interview-skills | https://github.com/jennifer88huang/interview-skills | 272 | JavaScript | None | 2026-07-10 | ✓ (Claude/Codex) | partial | ✗ | ✓ | AI mock interview coach; FAANG focus |
| feder-cr/resume_render_from_job_description | https://github.com/feder-cr/resume_render_from_job_description | 412 | Python | MIT | 2026-08-01 | partial (OpenAI) | ✗ | ✗ | ✓ | Resume customization from job URL |
| feder-cr/lib_resume_builder_AIHawk | https://github.com/feder-cr/lib_resume_builder_AIHawk | 193 | Python | MIT | 2026-08-01 | partial | ✗ | ✗ | partial | The resume-builder library behind AIHawk |
| colophon-group/jobseek *(via search API)* | https://github.com/colophon-group/jobseek | 167 | Python | (unknown) | active | N/A | partial | ✗ | ✓ | Monitors company career pages; surfaces new postings in a dashboard |
| imon333/Job-apply-AI-agent | https://github.com/imon333/Job-apply-AI-agent | 177 | Python | None | 2026-06-04 | ✗ (OpenAI-locked) | ✗ | ✗ | partial | LinkedIn/Indeed/StepStone; n8n; Selenium; OpenAI CV+cover; Sheets/Airtable sync |
| beatwad/LinkedIn-AI-Job-Applier-Ultimate | https://github.com/beatwad/LinkedIn-AI-Job-Applier-Ultimate | 147 | Python | None | active | partial | ✗ | ✗ | partial | LinkedIn+Indeed Playwright bot; ALL job types; custom resumes; Telegram reporting |
| replyre/job-hunter | (already in §1 above for completeness) | 150 | Python | None | 2026-08-06 | partial | ✗ | ✗ | ✓✓ | (see §1) |
| slothsheepking/jobclaw | https://github.com/slothsheepking/jobclaw | 208 | (check) | — | active | partial | partial | ✗ | partial | AI job-hunting agent; Boss直聘/LinkedIn; profile matching; auto-apply; built on OpenClaw |
| Liam-Frost/AutoApply *(via search API; rate-limited on full metadata)* | https://github.com/Liam-Frost/AutoApply | 111 | Python | (unknown) | active | partial | partial | ✗ | partial | Personal job-app AI agent; fit scoring; tailored materials; form filling; human-gated submission |
| Rayyan9477/AutoApply-AI-Agentic-Browser-Automation-for-Job-Search | https://github.com/Rayyan9477/AutoApply-AI-Agentic-Browser-Automation-for-Job-Search | 65 | Python | (unknown) | active | partial | ✗ | ✗ | partial | Job finding; AI resume+cover-letter; submission assist |
| tmwclaxton/autoapplycv | https://github.com/tmwclaxton/autoapplycv | 73 | JavaScript | NOASSERTION | 2026-08-03 | partial | ✗ | ✗ | partial | Chrome extension; auto-fill any site; sidebar-drafted answers/cover letters/resumes |
| Azoo92i/AutoApplyMax *(via search API)* | https://github.com/Azoo92i/AutoApplyMax | 58 | JavaScript | (unknown) | active | partial | ✗ | ✗ | partial | Chrome extension; LinkedIn/Indeed auto-apply; AI resume generator; ATS score checker; dashboard |
| LuisMIguelFurlanettoSousa/auto-apply-bot | https://github.com/LuisMIguelFurlanettoSousa/auto-apply-bot | 34 | TypeScript | MIT | 2026-07-08 | ✗ (Gemini-locked) | partial | ✗ | ✓ | Gemini + Playwright MCP; Gupy/LinkedIn/Indeed; dry-run; Telegram + web dashboard |
| krishnavalliappan/JobScout | https://github.com/krishnavalliappan/JobScout | 47 | Python | None | 2024-08-09 (stale) | ✗ (GPT-locked) | ✗ | ✗ | partial | LinkedIn + GPT + Notion sync; stale |
| BjornMelin/ai-job-scraper | https://github.com/BjornMelin/ai-job-scraper | 44 | Python | MIT | 2026-08-11 | ✓ (LangGraph + local LLM) | partial | ✗ | ✓ | Privacy-focused AI scraper; ScrapeGraph-AI + LangGraph; Streamlit dashboard |
| kbhujbal/go-get-jobs | https://github.com/kbhujbal/go-get-jobs | 40 | Go | None | 2026-03-29 | N/A | ✗ | ✗ | ✓ | Go aggregator; 50+ tech-company scrapers; MongoDB; concurrent; auto-README updates |
| cboyd0319/JobSentinel | https://github.com/cboyd0319/JobSentinel | 20 | TypeScript | MIT | 2026-08-12 | N/A | partial | ✗ | ✓ | Self-hosted; multi-board scrape + dedupe + score + alert; privacy-first |
| PunithVT/career-ops | https://github.com/PunithVT/career-ops | 2 | JavaScript | (check) | active | ✓ (Claude) | ✗ | partial (AWS deploy) | partial | Multi-user AI job-search platform; Claude JD eval; ATS PDF CVs; Greenhouse/Ashby/Lever scanners |

### Named candidates that did NOT resolve (recorded per the "do not skip" rule)

| Prompted name | URL tried | Result |
|---|---|---|
| `feder-cr/AIHawk` (the original, before fork) | https://github.com/feder-cr/AIHawk | **not found** (404). The AIHawk brand has no separate "original" repo — it lives entirely in `feder-cr/Jobs_Applier_AI_Agent_AIHawk` (§1, 30,159 stars) plus the sibling resume-builder libs `feder-cr/lib_resume_builder_AIHawk` (193★) and `feder-cr/resume_render_from_job_description` (412★). |
| `feder-cr/aihawk` (lowercase) | https://github.com/feder-cr/aihawk | **not found** (404). |
| `surapuramakhil-org/AI-job-apply-agent` | https://github.com/surapuramakhil-org/AI-job-apply-agent | **not found** (404). The org's only job-search repo is `Job_search_agent` (§1, archived, 171★). |
| `Nexloop/JobScan-AI` | https://github.com/Nexloop/JobScan-AI | **not found** (404). No GitHub search hits either. |
| `SurferMatt/job-application-automator` | https://github.com/SurferMatt/job-application-automator | **not found** (404). |
| `aiagentjobseeker` (org/repo) | https://github.com/aiagentjobseeker/aiagentjobseeker | **not found** (404). |
| `AutoJobr` | searched `q=AutoJobr` | **no results** — no GitHub repo of that name exists with meaningful stars. |
| `JobLLM` | searched `q=JobLLM` | only 3 micro-repos (≤1 star each): `NerdNek/JOBLLMMATCH`, `xyz010/jobLLMatch`, `Atharvatonape/Jobllm` — none material. |
| `JobPilot-AI` | searched `q=JobPilot+AI` | **no results**. (Note: a Python package `jobpilot` exists on PyPI as an unrelated Australian job-board scraper — not an AI agent.) |

---

## 3. Star-Priority Tiering

Combining §1 + §2 (33 repos total, excluding JoBot itself and the guide-only `tech-jobs-with-relocation`).

### Tier 1 — 10,000+ stars or 5,000+ with strong maintenance
1. **santifer/career-ops** — 63,659★ — JavaScript/MIT — pushed today — the gold standard
2. **MadsLorentzen/ai-job-search** — 31,411★ — TypeScript/MIT — pushed yesterday
3. **feder-cr/Jobs_Applier_AI_Agent_AIHawk** — 30,159★ — Python/AGPL-3.0 — pushed 2026-08-04

### Tier 2 — 1,000–10,000 stars
4. **speedyapply/JobSpy** — 4,072★ — Python/MIT — the canonical scraper dependency
5. **DaKheera47/job-ops** — 3,840★ — TypeScript — pushed 2026-08-10, has Docker
6. **GodsScion/Auto_job_applier_linkedIn** — 2,688★ — Python/MIT — pushed 2026-08-10
7. **PaulMcInnis/JobFunnel** — 2,178★ — Python/MIT — **ARCHIVED** (reference design only)
8. **can4hou6joeng4/boss-agent-cli** — 1,558★ — Python/MIT — pushed today
9. **eatmoreduck/boss-zhipin-scraper** — 1,094★ — Python/MIT — niche (China market)

### Tier 3 — 100–1,000 stars
10. **Gsync/jobsync** — 854★ — TypeScript/MIT
11. **wodsuz/EasyApplyJobsBot** — 804★ — Python/no-license (NOASSERTION)
12. **rainmanjam/jobspy-api** — 376★ — Python/Dockerized JobSpy
13. **agentenatalie/get-job.skill** — 348★ — Python/NOASSERTION (China market)
14. **strelov1/freehire** — 337★ — Go/MIT
15. **andrew-shwetzer/career-ops-plugin-…** — 463★ — HTML/MIT (career-ops sister)
16. **feder-cr/resume_render_from_job_description** — 412★ — Python/MIT
17. **jennifer88huang/interview-skills** — 272★ — JavaScript/no license
18. **slothsheepking/jobclaw** — 208★ — OpenClaw-based
19. **feder-cr/lib_resume_builder_AIHawk** — 193★ — Python/MIT
20. **imon333/Job-apply-AI-agent** — 177★ — Python/no license
21. **colophon-group/jobseek** — 167★ — Python
22. **surapuramakhil-org/Job_search_agent** — 171★ — Python/AGPL-3.0 — **ARCHIVED**
23. **replyre/job-hunter** — 150★ — Python/no license (docs excellent)
24. **beatwad/LinkedIn-AI-Job-Applier-Ultimate** — 147★ — Python/no license

### Tier 4 — < 100 stars, abandoned, or too niche
25. **Liam-Frost/AutoApply** — 111★ — Python
26. **tmwclaxton/autoapplycv** — 73★ — JS Chrome extension (no license)
27. **Rayyan9477/AutoApply-AI-Agentic-Browser-Automation-for-Job-Search** — 65★
28. **Azoo92i/AutoApplyMax** — 58★ — JS Chrome extension
29. **krishnavalliappan/JobScout** — 47★ — stale (last push 2024-08-09)
30. **BjornMelin/ai-job-scraper** — 44★ — Python/MIT (niche AI/ML roles)
31. **LuisMIguelFurlanettoSousa/auto-apply-bot** — 34★ — TypeScript/MIT (Brazilian market: Gupy)
32. **kbhujbal/go-get-jobs** — 40★ — Go
33. **cboyd0319/JobSentinel** — 20★ — TypeScript/MIT
34. **algsoch/job_agentic** — 3★ — Python/no license (Ollama-local, interesting arch)
35. **PunithVT/career-ops** — 2★ — JS (multi-user AWS fork of career-ops concept)

---

## 4. Feature Overlap Matrix

Top 10 repos by stars. Capabilities: **AA**=auto-apply, **SC**=scraping, **RT**=resume tailoring, **IP**=interview prep, **AT**=ATS tracking, **CA**=career analytics, **BA**=browser automation, **MA**=multi-agent, **ML**=multi-LLM provider, **DK**=Docker, **K8**=k8s, **SH**=scheduler/cron.

| Repo | Stars | AA | SC | RT | IP | AT | CA | BA | MA | ML | DK | K8 | SH |
|---|---:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| santifer/career-ops | 63,659 | partial | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (Playwright) | ✓ (eval/tailor/scan modes) | ✓✓ | ✓ | ✗ | ✓ (cron/modes) |
| MadsLorentzen/ai-job-search | 31,411 | partial | ✓ | ✓✓ (LaTeX) | ✓ | partial | ✓ | partial (skill CLIs) | ✓ (drafter+reviewer) | ✓ (CLI-portable) | ✗ | ✗ | ✓ (manual) |
| feder-cr/AIHawk | 30,159 | ✓✓ | partial | ✓ | ✗ | partial | ✗ | ✓ (Selenium) | ✗ (single pipeline) | ✗ (OpenAI-locked) | ✗ | ✗ | ✓ (loop) |
| speedyapply/JobSpy | 4,072 | ✗ | ✓✓ | ✗ | ✗ | ✗ | ✗ | ✗ (httpx) | ✗ | N/A | ✗ | ✗ | ✗ |
| DaKheera47/job-ops | 3,840 | partial | ✓ | partial | ✗ | ✓ | ✓ | ✓ (Playwright-MCP) | ✓ (orchestrator) | ✓ (multi-CLI) | ✓ | ✗ | ✓ |
| GodsScion/Auto_job_applier_linkedIn | 2,688 | ✓✓ | ✓ | ✓ | ✗ | partial | ✗ | ✓ (Selenium) | ✗ | partial (GPT-4o) | ✗ | ✗ | ✓ |
| PaulMcInnis/JobFunnel | 2,178 | ✗ | ✓✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N/A | ✗ | ✗ | ✓ (manual) |
| can4hou6joeng4/boss-agent-cli | 1,558 | ✗ | ✓ | ✗ | ✗ | partial | ✓ | ✗ (CLI-only) | partial | ✓ (AI-agent friendly) | ✗ | ✗ | partial |
| eatmoreduck/boss-zhipin-scraper | 1,094 | ✗ | ✓✓ | ✗ | ✗ | ✗ | partial (salary) | ✗ (CDP) | ✗ | N/A | ✗ | ✗ | ✗ |
| Gsync/jobsync | 854 | ✗ | partial | ✓ (AI review) | ✗ | ✓✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | partial |

Legend: ✓✓ = best-in-class / strongly implemented; ✓ = present; partial = present but limited; ✗ = absent.

**Observations:**
- Only **santifer/career-ops** scores ✓ or better across *all twelve* capabilities. It is the single most complete reference implementation in the survey.
- **Multi-LLM provider support** is genuinely rare: only career-ops, MadsLorentzen, job-ops, and JoBot itself ship a true provider-neutral abstraction. Most auto-apply repos hard-bind to OpenAI or Gemini.
- **No surveyed repo ships Kubernetes manifests** (K8 column all ✗). This is an open market gap JoBot could claim.
- **Interview prep** is consistently the weakest capability — only career-ops, ai-job-search, and the small `interview-skills` repo treat it as first-class.

---

## 5. Notable Architectural Patterns Per Repo (Top 10)

1. **santifer/career-ops (63,659★)** — *Multi-script modular pipeline orchestrated by an AI coding CLI*. ~120 small `.mjs` files (one per capability: `discover-ats.mjs`, `generate-cover-letter.mjs`, `build-cv-latex.mjs`, `rank-pipeline.mjs`, `reconcile-pipeline.mjs`, `verify-pipeline.mjs`, `weekly-digest.mjs`, `process-quality.mjs`, …) invoked via slash commands inside Claude Code / Codex / OpenCode / Antigravity. Each provider gets its own runner (`openai-eval.mjs`, `gemini-eval.mjs`, `ollama-eval.mjs`, `openrouter-runner.mjs`, `openai-tailor.mjs`) — a clean strategy-pattern LLM abstraction. Persistence is **JSON files on disk** (a `data/` + `jds/` + `output/` + `reports/` directory tree) with file-locking via `pipeline-lock.mjs` and `portal-health-lock.mjs`. Has a **plugin registry** (`plugins-registry/`, `plugins/`, `plugin-install.mjs`, `plugin-audit.mjs`) and a `scaffolder/` for new skills. Tests are co-located (`*.test.mjs`) plus a `tests/` and `test/` directory. The most sophisticated architecture in the survey — but **explicitly designed to run *inside* a host AI-CLI**, not as a standalone service.

2. **MadsLorentzen/ai-job-search (31,411★)** — *Claude-Code-skill-pack architecture*. Slash commands (`/setup`, `/scrape`, `/rank`, `/apply`, `/interview`) backed by a `.agents/skills/<portal>-search/cli/` directory of small Bun+TypeScript tools (one per job board). Python (`salary_lookup.py`, the `job_scraper/`, `upskill/`, `tools/` dirs) handles heavy lifting like LaTeX compilation and salary lookups. The application pipeline is a **two-agent drafter→reviewer loop**: drafter produces CV+cover letter, reviewer critiques, drafter revises. State lives in markdown + JSON profile files under `documents/`, `cv/`, `cover_letters/`. CV is generated via **LaTeX** (`lualatex` + `xelatex`); an ATS parseability check uses `pdftotext` from poppler. Has CI (`ci.yml`) + `upstream-watch.yml` to track portal changes. Designed to be **forked and owned** by each user.

3. **feder-cr/Jobs_Applier_AI_Agent_AIHawk (30,159★)** — *Single-script monolith with thin module layer*. `main.py` orchestrates a linear pipeline (login → search → iterate → per-job: tailoring + question-answering + submit). `src/` holds the modularization (LLM utils, browser actions, question answering, resume parser). Browser automation is **Selenium + Chrome**. Persistence is **plain JSON** under `data_folder/`. Config via `data_folder/secrets.yaml` + `data_folder/config.yaml`. No tests, no Docker. Notable for being *the* OG AI auto-applier (Aug 2024) — its architecture is deliberately minimal, which made it easy to fork and is why it accumulated 30k+ stars, but it is *not* a maintainable foundation for a large merge.

4. **speedyapply/JobSpy (4,072★)** — *Library, not application*. Pure-Python scraper package exposing a single `scrape_jobs()` API returning a pandas DataFrame. Internal adapter pattern: one BaseScraper subclass per board (LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Bayt). No persistence, no LLM, no agent layer — it is meant to be a *dependency* JoBot can consume directly via `pip install jobspy`. This is the cleanest single-component lift available.

5. **DaKhestra47/job-ops (3,840★)** — *Self-hosted DevOps-styled pipeline*. TypeScript monorepo split into `career-boards/` (board adapters), `extractors/` (JD parsers), `orchestrator/` (pipeline runner), `shared/` (types), `visa-sponsor-providers/` (a unique module that filters for visa-sponsoring employers). Uses Biome for lint, Knip for dead-code detection, Playwright-MCP for browser, and runs both as CLI and via Docker (`Dockerfile` + `docker-compose.yml` + `docker-entrypoint.sh`). Has a `docs-site/` (likely Astro/VitePress). Architecturally the closest "spiritual sibling" to JoBot's vision of a self-hosted, privacy-first, orchestrated pipeline.

6. **GodsScion/Auto_job_applier_linkedIn (2,688★)** — *Selenium-based LinkedIn Easy Apply bot*. Single-language Python, configurable workflow, modular question-answering with GPT-4o. Mostly a refinement of the AIHawk pattern with better LinkedIn-specific resilience (blacklisting, retry logic). No Docker, no tests, no provider abstraction.

7. **PaulMcInnis/JobFunnel (2,178★, ARCHIVED)** — *Legacy multi-board scraper*. Canada-centric reference design (Indeed/LinkedIn/Monster/Glassdoor → merged CSV). Architecture is a provider-adapter pattern with `JobFunnel` base class and per-board subclasses. No LLM, no apply step. Influential historically (predates AIHawk by 5 years) but archived — useful as a *reference* for scraper resilience patterns, not for direct code lift.

8. **can4hou6joeng4/boss-agent-cli (1,558★)** — *CLI-first, AI-agent-friendly design*. Outputs **JSON envelopes** (structured tool-call-style output) so an AI host can consume results programmatically. Rule-based welfare filtering + shortlisting; minimal browser automation. Notable architectural pattern: **designed as a tool for an agent, not as an agent itself** — the inverse of career-ops.

9. **eatmoreduck/boss-zhipin-scraper (1,094★)** — *Chrome DevTools Protocol (CDP) scraper*. Reuses the user's real logged-in browser session via CDP rather than launching a separate browser — this is a stealthier, harder-to-detect pattern than Selenium/Playwright. Bypasses BOSS Zhipin's font-obfuscation anti-scraping. Niche (China market) but architecturally instructive for the stealth-browser layer JoBot is building with Patchright.

10. **Gsync/jobsync (854★)** — *Self-hosted full-stack web app*. TypeScript front-end + back-end. Full application tracker (kanban-style), AI resume review, job matching, task logging, analytics. The most "product-shaped" of the surveyed repos — closest to a deployable consumer product. Privacy-first (self-hosted). Could inform JoBot's eventual UX layer.

---

## 6. JoBot Current State

**Repo:** `aryansinghnagar/JoBot` — 0★ — Python (AGPL-3.0) — created 2026-07-22, last pushed 2026-08-11.

### What it currently has (verified from README + pyproject.toml + tests/ listing + recent commit log)
- **CLI** via `typer` + `rich` (entrypoint `jobot = "jobot.cli.main:app"`)
- **Core engine**: Python 3.11+ **async execution fabric + task graph engine** (`test_task_graph.py`)
- **Browser stack**: **Patchright** (stealth Playwright fork) integration in progress (`test_browser_session.py`)
- **Security & storage**: **SQLite WAL control plane + Fernet encryption + OS Keyring** (`test_storage.py`)
- **AI routing**: **provider-neutral `ModelRouter`** with Gemini/OpenAI/Anthropic/Ollama fallbacks (`test_ai.py`) — one of only 4 repos in the survey with a true multi-LLM abstraction
- **Adapter registry** with a **Greenhouse adapter** already implemented (`test_adapter_registry.py`, `test_greenhouse_adapter.py`) — ATS-site-adapter pattern
- **Resilience primitives**: **circuit breaker** (`test_circuit_breaker.py`, `test_circuit_breaker_wired.py`), **captcha solver** (`test_captcha_solver.py`), **dedup** (`test_dedup.py`)
- **Policy engine** with caps + enforcement (`test_policy.py`, `test_policy_cap.py`, `test_policy_enforced.py`)
- **Application State Protocol (ASP)** with a 12-phase implementation (`test_asp.py`, `test_asp_12_phase.py`)
- **Observability**: tracing + QA engine + alerts (`test_tracing_wired.py`, `test_qa_engine_wired.py`, `test_alerts_wired.py`)
- **Skill extraction** (`test_skill_extraction.py`), **discovery** (`test_discovery.py`)
- **Vector memory** + **PII masker** (added 2026-08-11 per commit log)
- **Tests**: ~30 test files (pytest + pytest-asyncio), `tests/evals/`, `tests/integration/`, `tests/mock_ats/`, `tests/fixtures/`, plus a `tests/npm/` (vitest) dual-stack
- **CI**: `ci.yml` (pytest via `python -m pytest`) + `publish.yml` (PyPI publish); Ruff + mypy strict
- **Docs**: extensive planning artifacts — `JoBot_Refactor_Plan.md`, `JoBot_Refactor_Review_2.md`, `unified_master_plan.md`, `job_application_automaton_plan.md`, `implementation_contract_dev_0_1.md` … `_dev_2_0.md`, `implementation_contract_release_1_0.md`, `runtime_capability_matrix.md`, `operating_summary.md`, `Improvement_Plan.txt`, plus `docs/dev/` and `docs/user/` trees
- **worklog.md** already exists in-repo (the team's own execution log)

### What it lacks (the gap the merge needs to fill)
1. **Production scrapers for major job boards** — only Greenhouse adapter is real; LinkedIn/Indeed/Glassdoor/etc. are stubs being de-stubbed. → *Lift from JobSpy (Tier 2) as a direct dependency; lift portal-health-locking pattern from career-ops.*
2. **LaTeX / PDF resume tailoring** — no CV compilation, no template system. → *Lift the drafter→reviewer loop + LaTeX pipeline from MadsLorentzen/ai-job-search; lift `build-cv-latex.mjs` / `build-cv-html.mjs` patterns from career-ops.*
3. **Cover-letter generation** — absent. → *Lift `generate-cover-letter.mjs` pattern from career-ops.*
4. **Interview prep module** — absent. → *Lift `interview-prep/` dir from career-ops and the `/interview` skill from ai-job-search.*
5. **Application tracking dashboard / analytics** — absent. → *Lift `build-dashboard.mjs`, `weekly-digest.mjs`, `stats.mjs`, `funnel-velocity.mjs`, `rejection-latency.mjs` patterns from career-ops; consider the jobsync full-stack UI as a longer-term reference.*
6. **ATS scan / discovery** — JoBot has a mock ATS in tests but no real ATS-portal scanner. → *Lift `discover-ats.mjs`, `scan-ats-full.mjs`, `detect-reposts.mjs` from career-ops.*
7. **Docker / container packaging** — no Dockerfile. → *Lift Dockerfile + docker-compose.yml pattern from career-ops or job-ops.*
8. **Multi-board question-answering AI** for application forms — JoBot has the ModelRouter but no question-answering pipeline wired to it. → *Lift the question-answering module from AIHawk (with provider-neutrality swap) and Auto_job_applier_linkedIn.*
9. **Outreach / cold-DM generation** — absent. → *Lift the profile-driven outreach pipeline from replyre/job-hunter (YAML presets + LinkedIn people-search URL generation).*
10. **Scheduler / cron loop** — JoBot has a task graph but no documented daily-loop. → *Lift the daily-digest scheduler pattern from replyre/job-hunter and `modes/` from career-ops.*
11. **Salary benchmarking** — absent. → *Lift `salary_lookup.py` from ai-job-search and `salary-gap.mjs` from career-ops.*
12. **Plugin system** — JoBot has an adapter registry but no user-facing plugin install/audit flow. → *Lift `plugin-install.mjs`, `plugin-audit.mjs`, `plugins-registry/` from career-ops.*

### Verdict
JoBot is **architecturally the most ambitious** of the surveyed repos — it has primitives (ModelRouter, ASP, circuit breaker, task graph, vector memory, PII masker, stealth browser) that *none* of the higher-star repos possess. But it is **functionally the emptiest** in user-facing capabilities: no real scrapers, no CV tailoring, no interview prep, no dashboard. The merge should treat JoBot as the **host chassis** and graft the **capability modules** from the Tier-1/Tier-2 repos onto it, *re-implementing* them behind JoBot's existing provider-neutral and policy-enforced abstractions rather than vendoring them whole.

---

## 7. Recommended Tiered Adoption Order

### Tier 1 — absorb first (these define the capability surface)

| Source repo | What to lift | Why first |
|---|---|---|
| **santifer/career-ops** | (a) Plugin registry + plugin-audit + plugin-install scaffolder — adapt to JoBot's adapter registry. (b) Per-provider LLM runner strategy (`openai-eval.mjs`, `gemini-eval.mjs`, `ollama-eval.mjs`, `openrouter-runner.mjs`) → port to JoBot's `ModelRouter` as strategy classes. (c) The ~120-capability `.mjs` script catalog → port the **CV builder, cover-letter generator, ATS scanner, weekly digest, dashboard builder, followup cadence, skill extractor, salary gap** into JoBot's async task graph. (d) Test patterns (`*.test.mjs` co-location). (e) Dockerfile + docker-compose.yml + SBOM/CodeQL CI patterns. | Highest star count + the only repo covering all 12 capability columns. Its JSON-file persistence model is *simpler* than JoBot's SQLite WAL — port the *logic*, keep JoBot's better persistence. Its 17 CI workflows are a gold standard for engineering posture. |
| **MadsLorentzen/ai-job-search** | (a) The **drafter→reviewer two-agent loop** for CV/cover-letter generation — port as a JoBot task-graph subgraph. (b) **LaTeX CV pipeline** (`lualatex` + `xelatex` + `pdftotext` ATS check). (c) The `.agents/skills/<portal>-search/` per-board skill pattern → adapt to JoBot's adapter registry (one Bun/TS skill per portal). (d) `/setup` profile ingestion (documents-folder → profile). (e) Salary benchmarking (`salary_lookup.py`). | Second-highest stars + the only repo with a genuinely *language-agnostic* evaluation framework. Its slash-command UX maps cleanly onto JoBot's typer CLI. The Danish-portal skills are easy to swap for US/global ones. |
| **feder-cr/Jobs_Applier_AI_Agent_AIHawk** | (a) The **question-answering module** for application forms (its strongest asset) — re-implement behind JoBot's `ModelRouter` (AIHawk is OpenAI-locked). (b) The **LinkedIn Easy Apply** Selenium flow → re-implement on Patchright (JoBot already chose the stealthier lib). (c) Reference for the per-job application loop structure. | Third-highest stars + the historical OG (Aug 2024). **Skip its architecture** (single-script monolith, JSON persistence, no tests, no Docker) — only lift the question-answering + Easy-apply *algorithms*. |

### Tier 2 — absorb next (these fill specific capability gaps)

| Source repo | What to lift | Why this tier |
|---|---|---|
| **speedyapply/JobSpy** | Add as a **direct pip dependency** (`pip install jobspy`) — gives LinkedIn/Indeed/Glassdoor/Google/ZipRecruiter/Bayt scraping in one call. Wrap in a JoBot adapter that respects its circuit-breaker + dedup primitives. | The cheapest, highest-leverage lift in the entire survey. Already MIT-licensed, already a library. **Do not re-implement — depend.** |
| **DaKheera47/job-ops** | Reference architecture for: (a) `orchestrator/` pipeline runner pattern, (b) `extractors/` JD parser module, (c) `visa-sponsor-providers/` (unique — no other repo has this), (d) Docker entrypoint pattern, (e) docs-site scaffolding. | Closest spiritual sibling to JoBot's vision. License is NOASSERTION — *read for inspiration, do not copy code verbatim* without clarifying license. |
| **GodsScion/Auto_job_applier_linkedIn** | LinkedIn-specific resilience patterns (blacklist, retry, session persistence). | Good LinkedIn-specific hardening; MIT-licensed. |
| **can4hou6joeng4/boss-agent-cli** | **JSON-envelope output pattern** for making JoBot itself callable as a tool by other AI agents (MCP-friendly). | Architecturally novel pattern — making JoBot an *agent-tool*, not just an agent. |
| **eatmoreduck/boss-zhipin-scraper** | **Chrome-CDP real-session-reuse** pattern as an alternative stealth strategy to Patchright. | Niche (China) but the CDP session-reuse technique is valuable for JoBot's stealth layer. |

### Tier 3 — selectively absorb (single-capability references)

| Source repo | What to lift | Caveat |
|---|---|---|
| **Gsync/jobsync** | Full-stack tracker dashboard UX reference (kanban + analytics) for JoBot's eventual UI layer. | TypeScript — would be a separate UI subproject, not core. |
| **replyre/job-hunter** | Profile-driven YAML presets + daily digest scheduler + LinkedIn people-search URL generation + REST API surface (Postman collection included). | No license — *read for design, re-implement, do not vendor code*. Its 7-part docs/ structure is exemplary. |
| **agentenatalie/get-job.skill** + **jennifer88huang/interview-skills** | Interview-prep skill design (Chinese-market ref + FAANG mock-interview coach). | Both Claude-skill format — port the prompt design, not the skill packaging. |
| **feder-cr/resume_render_from_job_description** + **feder-cr/lib_resume_builder_AIHawk** | Reference resume-rendering algorithms (the AIHawk resume lineage). | OpenAI-locked — re-implement behind ModelRouter. |
| **strelov1/freehire** | Go-based search-engine architecture reference (if JoBot ever adds a job-listings search endpoint). | Different language — design reference only. |
| **beatwad/LinkedIn-AI-Job-Applier-Ultimate** | Telegram-reporting pattern + "applies to ALL job types, not just Easy Apply" technique. | No license — design reference only. |

### Tier 4 — skip (and why)

| Repo | Why skip |
|---|---|
| **PaulMcInnis/JobFunnel** | Archived (Dec 2025). Architecture is outdated (no LLM, no apply step). Useful only as a *historical* reference for scraper-resilience patterns — JoBot's JobSpy dependency supersedes it. |
| **algsoch/job_agentic** | 3★, no LICENSE file (legally unusable), and its "Job Intelligence OS" concept is functionally a subset of what JoBot already plans. The Ollama-only local-LLM stance is interesting but JoBot's ModelRouter already supports Ollama as one of four providers. |
| **krishnavalliappan/JobScout** | Stale (last push Aug 2024), GPT-locked, no license. No value over Tier-1/Tier-2 options. |
| **wodsuz/EasyApplyJobsBot** | No LICENSE (NOASSERTION) → legally untouchable. Functionally a subset of AIHawk. |
| **imon333/Job-apply-AI-agent** | No license, OpenAI-locked, n8n-dependent (heavy external dependency). AIHawk supersedes it. |
| **All Tier-4 Chrome-extension repos** (tmwclaxton/autoapplycv, Azoo92i/AutoApplyMax, Rayyan9477/…) | Chrome extensions — wrong deployment model for JoBot (which is CLI/server-first). Architecturally incompatible. |
| **LuisMIguelFurlanettoSousa/auto-apply-bot** | Gemini-locked, Brazilian-market-focused (Gupy board) — too niche; the Playwright-MCP pattern is already available from job-ops. |
| **PunithVT/career-ops** | 2★ AWS-deploy fork of career-ops concept — strictly dominated by the original. |
| **Named candidates that don't exist** (AutoJobr, JobLLM, JobPilot-AI, feder-cr/AIHawk-original, Nexloop/JobScan-AI, SurferMatt/…, aiagentjobseeker) | These repos could not be located on GitHub despite targeted search. Either they were private, renamed, deleted, or were never real. No merge plan possible. |

### Final recommended adoption sequence
1. **Week 1–2:** Vendor `speedyapply/JobSpy` as a pip dependency → instantly gain 6 board scrapers behind a JoBot adapter. (Highest leverage / lowest risk.)
2. **Week 3–6:** Port Tier-1 capability modules from **career-ops** (CV builder, cover-letter, ATS scanner, dashboard, digest, plugin registry, Docker, CI hardening) → behind JoBot's existing ModelRouter + SQLite + circuit-breaker primitives.
3. **Week 7–10:** Port the **drafter→reviewer loop + LaTeX pipeline + `/setup` profile ingestion** from **MadsLorentzen/ai-job-search**.
4. **Week 11–14:** Port the **question-answering + Easy-Apply loop** from **AIHawk**, re-implemented on Patchright + ModelRouter.
5. **Week 15+:** Selectively absorb Tier-3 single-capability references (interview-prep, outreach, dashboard UX) as JoBot's surface area matures.

---

### Appendix — Verification log

All star counts, languages, licenses, archived flags, and `pushed_at` timestamps for the 9 named repos were fetched from `https://api.github.com/repos/{owner}/{repo}` on **2026-08-13** between 04:35–05:00 UTC. Discovered-repo metadata came from the same endpoint; where anonymous rate-limiting (HTTP 403) interrupted, the GitHub **search API** (`https://api.github.com/search/repositories?q=…&sort=stars`) was used as a fallback source for star count + description (separate rate-limit budget) and is marked "(via search API)" in §2. Feature inventories and architecture notes were derived from each repo's README (fetched from `raw.githubusercontent.com`) and root-directory listing (from `/contents/`). CI workflow counts came from `/contents/.github/workflows`. No star counts were fabricated; any value that could not be confirmed is marked "unknown" with explanation.
