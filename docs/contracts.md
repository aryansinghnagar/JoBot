# Frozen Public Interfaces (Merge Contract)

**Phase 0.5 deliverable of the JoBot Merge Plan (§21.1).** These are the
existing public contracts that the merge **must not break**. Any change to a
frozen signature requires an explicit plan amendment before merge work starts.

The merge plan (§21.1 step 0.5) freezes: `BoardAdapter`, `ApplyRequest/Result`,
`ModelRouter.route()`, `BlobStore`, `PolicyEngine.check_apply()`. The table
below maps those *target* names to the **actual code** — where a name differs,
the code name is canonical and the plan name is not yet implemented.

## Frozen Contracts (actual code)

| Merge-plan name | Actual symbol | Location | Signature (public surface) |
|---|---|---|---|
| BoardAdapter | `SiteAdapter` (ABC) | `src/jobot/adapters/base.py` | `login(username?, password?) -> bool`; `parse_job_posting(url) -> JobPosting`; `fill_form(job, profile, application) -> dict`; `submit_application(application) -> bool`; `verify_submission(application) -> VerificationResult`; `extract_form_questions(job) -> list[str]` (default impl); `capture_screenshot() -> bytes\|None` |
| ApplyRequest / ApplyResult | `Application` (pydantic) — no separate request/result types exist | `src/jobot/models/domain.py` | One model carries intent through verification: `application_id`, `job_id`, `site`, `profile_id`, `status: ApplicationStatus`, `idempotency_key`, `trust_level: TrustLevel`, `form_values: dict`, `evidence: list[EvidenceItem]`, `error_message` |
| ModelRouter.route() | `ModelRouter.generate_text()` | `src/jobot/ai/router.py` | `async generate_text(prompt, system_prompt=None, fallback_chain=None) -> str`; cost tracking via `daily_budget_usd` / `current_spent_usd` / `metrics_history`; `ModelProvider` = `GEMINI \| OPENAI \| ANTHROPIC \| OLLAMA` |
| BlobStore | `CredentialVault` + `DatabaseManager` — no blob store exists yet | `src/jobot/storage/vault.py`, `src/jobot/storage/db.py` | Vault: `encrypt_data / decrypt_data / save_encrypted_profile / load_encrypted_profile` (Fernet + OS keyring). DB: `save_job_posting / get_job_posting / save_application / get_application / get_application_by_idempotency_key / application_exists / list_applications / get_daily_application_count / clear_all_applications` (SQLite WAL) |
| PolicyEngine.check_apply() | `PolicyEngine.evaluate_application_policy()` + `check_application_policy()` | `src/jobot/policy/engine.py` | `check_application_policy(job, profile, application, daily_submitted_count) -> PolicyEvaluationResult` (`allowed`, `requires_approval`, `violations`, `blocking_reason`) |
| (pipeline entrypoint) | `ApplicationSubmissionPipeline.execute()` | `src/jobot/asp/pipeline.py` | `async execute(job_url, profile, auto_approve=False) -> Application`; plus `submit_and_verify(app) -> Application`. See `docs/asp.md` |

## Invariant Rules

1. **No breakage without amendment** — signatures above are frozen for the
   duration of the merge. Additive changes (new methods, new optional params
   with defaults) are allowed; renames/deletions are not.
2. **Profile facts are canonical** — pydantic models must keep the existing
   fields; the merge may add fields but must not change serialized field names
   used by the encrypted profile (`~/.jobot/profiles/default.enc`).
3. **Idempotency semantics preserved** — `get_application_by_idempotency_key`
   + `DUPLICATE_SKIPPED` behavior is contract (`tests/test_dedup.py`).
4. **Enums are closed sets** — adding `ApplicationStatus` / `PipelinePhase` /
   `TrustLevel` members is allowed; renaming or removing existing members is
   not.

## Known Limitations (do not "fix" during merge without a plan amendment)

- `GenericPortalAdapter` (`src/jobot/adapters/more_adapters.py`) serves 9
  portals (glassdoor, ziprecruiter, shine, foundit, hirist, instahyre, cutshort,
  wellfound, smartrecruiters) and **fabricates placeholder job postings**
  (hardcoded descriptions). The merge plan's scraper module (§12) replaces
  this; until then it is the registered implementation.
- `ModelRouter` has no `route()` / `route_with_tools()`; providers other than
  Gemini/OpenAI/Anthropic/Ollama (Bedrock, Vertex, Mistral, Cohere,
  OpenAI-compatible) land in Phase 1 of the merge plan.
- `PolicyEngine` caps are per-site daily limits; plan-target caps
  (weekly/cost/board blacklist, `require_human_approval_above_cost_usd`) land
  later.

## Verification

- Registry/import freeze: `python -m pytest tests/test_adapter_registry.py tests/test_adapters_extra.py`
- Idempotency freeze: `tests/test_dedup.py`
- ASP freeze: `tests/test_asp_12_phase.py`, `tests/integration/test_pipeline_12_phase.py`
- Storage freeze: `tests/test_storage.py`
- Policy freeze: `tests/test_policy*.py`, `tests/integration/test_policy_integration.py`

## Phase 1 Addendum (2026-08-13)

The `jobot/llm/` package (plan.md Chapter 6) landed without breaking any frozen
signature:

- **`ModelRouter.generate_text(prompt, system_prompt=None, fallback_chain=None)`**
  is preserved — `src/jobot/ai/router.py` is now a re-export shim of
  `jobot.llm.router.ModelRouter`. Additive-only changes: `task=` kwarg and
  `complete()` / `health_check()` / `list_configured_providers()` methods.
- **New providers** (12 registry entries): `GeminiProvider`, `OpenAIProvider`,
  `AnthropicProvider` (refactored from the old `_call_provider`),
  `OpenAICompatProvider` (openrouter/groq/together/ollama/vllm), `MistralProvider`,
  `CohereProvider` (HTTP-native), `BedrockProvider` (boto3, optional
  `[providers]` extra), `VertexProvider` (google-genai vertex client).
- **Costing**: `src/jobot/llm/pricing.yaml` (package data) + user override at
  `~/.jobot/pricing.yaml`; `LLMProvider.estimate_cost()` per model.
- **Daily cost cap**: `llm.daily_cost_cap_usd` (default 5.00), spend persisted
  to `~/.jobot/data/llm_spend.json` (date-keyed, survives restarts).
- **Secrets**: `jobot.secrets` wraps the OS keyring (service `jobot`); key
  lookup order is env var → keyring (`llm.api_key.<provider>`).
- **Config surface**: `jobot config get/set/unset/show` (three-tier: env →
  keyring → `~/.jobot/config.yaml`; secrets masked on `show`) and
  `jobot doctor` (exit 0 with ≥1 provider configured).
- **Profiles YAML**: `~/.jobot/profiles/<name>.yaml` (`JOBOT_PROFILE` select)
  holds **non-identity** config only (search/target/resume_base/llm/outreach);
  identity facts remain canonical in the Fernet vault — no second source of
  truth was introduced.
- **Live tests opt-in**: `JOBOT_RUN_LIVE_LLM=1 pytest tests/integration/test_llm_providers_live.py`.

## Phase 2 Addendum (2026-08-13)

The scraper layer (plan.md Chapter 12 + §316–325) landed without breaking any
frozen signature:

- **`GreenhouseAdapter` fabrication removed** — `parse_job_posting` now raises
  on fetch error instead of returning invented title/description;
  `discover_matching_jobs(board_token, limit)` delegates to the new honest
  `discover_jobs(company, limit=25, keywords="", location="")` which returns
  `[]` on failure (no fabricated postings anywhere in the real-feed path).
  `fill_form` / `submit_application` / `verify_submission` unchanged.
- **`JobDiscoveryEngine.discover_matching_jobs`** extended additively:
  `companies=None, location=""` kwargs added; default `active_portals` now
  maps to real feeds only. Portals without a public feed (`UNSCRAPABLE_BOARDS`:
  workday, instahyre, cutshort, wellfound, shine, foundit, hirist, ziprecruiter,
  naukri, glassdoor) are skipped with a warning — never fabricated.
- **New scraper package** `src/jobot/scrapers/` (discovery-only, no frozen
  surface affected):
  - `jobspy.py` — `JobSpyAdapter(board, delay_s=1.0, proxies=None)` over
    `JOBS_BOARDS` (linkedin, indeed, glassdoor, google, zip_recruiter, bayt,
    naukri, bdjobs); uniform protocol `discover_jobs(keywords="", location="",
    limit=25, hours_old=72, country_indeed="USA", is_remote=False,
    job_type=None)`. The `python-jobspy` library is **not** a declared
    dependency (metadata pins `NUMPY==1.26.3` → unresolvable on py3.14);
    install via `pip install python-jobspy==1.1.82 --no-deps` and it is
    import-guarded (`JobSpyNotInstalledError`).
  - `ats.py` — `AtsFamilyAdapter` base + `LeverAdapter` / `AshbyAdapter` /
    `SmartRecruitersAdapter` (`FAMILY_ADAPTERS`), all with the uniform
    `discover_jobs(company=None, limit=25, keywords="", location="")` protocol.
    Lever uses the current API schema (`text` = title; description in
    `descriptionPlain`; `categories.location`; `hostedUrl`). Workable has no
    anonymous feed (per-account keys) — deliberately not implemented.
  - `careers.py` — `CareerPageScanner(companies=...)`: fingerprints a company
    careers page from `career_sites.yaml` markers and dispatches to the
    matching family adapter; workable fingerprints log-and-skip. Verified
    starter set (2026-08-13 live): webflow/figma/vercel → greenhouse,
    notion/benchling → ashby.
  - `dedup.py` — `DedupService(db=None, threshold=0.92)`: tier 1 exact sha256
    over normalized title|company|location; tier 2 cosine ≥ threshold over a
    local char-bigram pseudo-embedding of the **title** (dim 64). Persists to
    the new `job_dedup_cache` table (additive, no migration).
- **`jobot.memory.vector.simple_embedding`** upgraded in place (deterministic,
  order/punctuation-insensitive char-bigram bag; same signature) — used by
  `VectorMemory` retrieval and dedup tier 2.
- **New config keys**: `scraper.jobspy.delay_s` (default 1.0),
  `scraper.jobspy.proxy_list` (comma-separated, optional).
- **New CLI commands**: `jobot scrape <board> [--keywords --location --limit
  --companies --all --json --no-dedup --hours-old --country]` (real postings
  only; `--json` keeps stdout pure JSON, progress on stderr) and
  `jobot dedup [--stats]` (dedup cache view).
- **Exit criterion (plan.md:325)**: `jobot scrape linkedin --keywords 'senior
  backend' --location 'San Francisco' --limit 50` returned 50 real postings on
  a non-throttled IP (repeated runs are subject to LinkedIn's per-IP rate
  limiting; indeed returned 27+ real postings). Repost reduction ≥80% is
  enforced by `tests/test_scrapers_dedup.py::test_repost_reduction_meets_exit_criterion`.
- **Live tests opt-in**: `JOBOT_RUN_LIVE_SCRAPE=1 pytest tests/integration/test_scrape_live.py`.
- **CI note**: mypy targets `python_version = "3.12"` (numpy 2.5+ ships
  pyi stubs with 3.12-only syntax; `src/` itself remains 3.11-compatible —
  CI tests run on 3.11/3.12).

## Phase 3 Addendum (2026-08-13)

The document stack + auto-apply orchestration (plan.md §327–339) landed without
breaking any frozen signature:

- **New `jobot.documents` package** (no frozen surface affected):
  - `compiler.py` — `ResumeData`, `compile_resume_data(profile, job, experiences)`
    (bullets merged only for real profile experience rows), `escape_latex`,
    `render_tex(template, data)`, `to_plain_text`. Templates ship as package
    data (`jobot/documents/templates/{default,modern,classic}.tex.j2`,
    `[tool.setuptools.package-data]`).
  - `engines.py` — pluggable render stack: `LuaLaTeXRenderer` (plan-faithful
    TeX path) with pure-python fallback `FallbackPdfRenderer` (reportlab).
    `get_renderer(engine="auto")` picks TeX when `lualatex` is on PATH, else
    fallback. ASCII-only glyphs in the fallback (`- ` bullets) because
    pdfminer mis-extracts `&bull;`/`&mdash;` as `(cid:…)`.
  - `ats.py` — `AtsScorer` (density band 0.15–0.95, ≥2 bullets, header
    regex `WORK EXPERIENCE`, threshold 0.85) + pdftotext/pdfminer extractors;
    `score_pdf_file` is extractor-agnostic.
  - `tailor.py` — `DocumentTailor` rewritten around `TailorLoop` (≤3
    iterations, A–F reviewer rubric, PASS on LLM degradation). Grounding:
    deterministic `verify_fact_truthfulness_detailed(text, profile, job)` —
    skill claims must be in profile skills, traceable to profile experience/
    education text, or absent from the common-tech lexicon
    (`SkillExtractor.COMMON_TECH_KEYWORDS`). On `DEGRADATION_TEXT` the draft
    falls back to profile facts verbatim (never LLM-invented).
  - `cover.py` — `CoverLetterGenerator.generate(job, profile, matching_skills,
    tone, extra_prompt)` with 5 tone presets (classic/narrative/technical/
    brief/enthusiastic), `task="cover_letter"`.
  - `pdf_exporter.py` — `ResumeExporter.export_resume_pdf(profile, job, tone,
    template, engine, output_dir) -> (Path, AtsScore)`; keeps the frozen
    `.txt`/`.html` export contract.
- **New `jobot.asp` orchestration**:
  - `saga.py` — `ApplySaga` (start/resume/checkpoint/fail/compensate/cancel/
    complete) over new `saga_instances`/`saga_steps` tables (additive).
  - `orchestrator.py` — `ApplyOrchestrator.apply(job, profile, auto_approve,
    resume_saga_id, ...)`: tailor → grounding gate → artifacts → pipeline.
    Supervised stops at `PENDING_APPROVAL` with artifacts attached to the
    saved record; `submit_approved(app)` runs phases 11–12. Compensation:
    CIRCUIT_OPEN → quarantine; other failures → app REJECTED with evidence,
    saga COMPENSATED; `DUPLICATE_SKIPPED` completes the saga.
  - `pipeline.py` — added `extra_form_data` param, merged in
    `_handle_phase_11_submit` immediately before submission; phase ordering
    and status contract unchanged (tested).
- **Adapters (honesty hardening)**: `lever.py` rewritten against the real
  Lever API (`api.lever.co/v0/postings/{company}/{id}?mode=json`); resume
  attachment as `content_base64` on `greenhouse.py`; `linkedin.py` raises
  `NotImplementedError` with an honest message (Easy Apply handled by the
  saga instead). `Application` gains `job_url: Optional[str]` (additive).
  Adapters capture real confirmation ids (`_lever_confirmation_id`,
  `_greenhouse_confirmation_id`); `verify_submission` is honest when the id
  is absent (returns `success=False`, never fabricated).
- **LinkedIn Easy Apply saga**: `stealth/linkedin_easy_apply.py` —
  selector-driven state machine (open modal → answer fields via
  `QAEngine`/answers overrides → review/submit → evidence screenshots),
  explicit failure when no Easy Apply button is present. Hermetic tests use a
  Flask harness (`tests/mock_linkedin/`) + FakeBrowser; live runs are
  opt-in via `JOBOT_RUN_LIVE_BROWSER=1`.
- **New CLI commands**: `jobot apply <job-id|--url> [--dry-run --approve
  --resume <saga> --template --tone --extra-prompt --engine]`, `jobot
  coverletter`, `jobot qa`, `jobot resume {runner|tailor|ats-check|templates}`
  (no-arg = runner resume, unchanged), `jobot scrape --save`. New config:
  `resume_template`, `cover_letter_tone`, `qa_engine`. `jobot doctor` adds
  informational LaTeX/pdftotext engine checks (non-fatal; reportlab always
  available).
- **Exit criterion (plan.md:339)**: `jobot apply --dry-run` produces a
  tailored PDF (ATS ≥ 0.85) + cover letter; enforced by
  `tests/test_saga_orchestrator.py` (dry-run ATS ≥ 0.85) and
  `tests/test_documents_stack.py`.
- **Live tests opt-in**: `JOBOT_RUN_LIVE_BROWSER=1 pytest
  tests/integration/test_linkedin_easy_apply_live.py`.
- **New core deps**: `jinja2>=3.1.0`, `reportlab>=4.0.0`,
  `pdfminer.six>=20240706`.
## Phase 4/5 Addendum (2026-08-15, release-1.0)

- **Tracker**: `src/jobot/tracker/` (analytics.py, render.py, dashboard
  HTML); db columns `responded_at`/`outcome`; CLI `jobot tracker {stats|
  dashboard-html|table}`.
- **Digest/scheduler**: `src/jobot/digest/`, `src/jobot/notify/email.py`
  (SMTP via `smtp.*` config keys; digest dry-run by default, `--send` to
  email), `src/jobot/scheduler/` � CLI `jobot digest`, `jobot loop` (4 modes:
  watch/apply/digest/status). `jobot status` also shows digest/loop state.
- **Interview**: `src/jobot/interview/` � STARCoach + MockInterviewer,
  question banks in package-data (`jobot.interview = questions/*.json`);
  CLI `jobot interview`.
- **Analytics**: `src/jobot/analytics/` � SkillGapAnalyzer +
  SalaryBenchmarker; CLI `jobot skill-gap`, `jobot salary`. Salary uses a
  shipped YAML default (`data/salaries.yaml`, package-data) plus live opt-in
  via `JOBOT_RUN_LIVE_SALARY=1` with 24h cache + circuit breaker + silent
  fallback to defaults (never fabricated figures).
- **Outreach**: `src/jobot/outreach/` � LinkedInPeopleSearchURLBuilder,
  DMGenerator, OutreachGate (daily DM cap from config); presets in
  package-data (`jobot.outreach = presets.yaml`); CLI `jobot outreach`.
- **Plugins**: `src/jobot/plugins/` � PluginManifest (schema v1),
  PluginInstaller, PluginAuditor; CLI `jobot plugin {install|list|audit|
  remove}`.
- **Docker/CI**: multi-stage `Dockerfile` + `docker-compose.yml`
  (`.dockerignore`); CI: CodeQL workflow, SBOM + provenance attestation job.
- **Phase 5 honest adapters (no fabrication � release invariant)**:
  - `naukri`: `submit_application` clicks the real Apply button and returns
    True only on a success indicator (also detects already-applied);
    `verify_submission` navigates `https://www.naukri.com/mnjuser/myapplications`
    and matches the job; both return honest failures (never fabricated
    confirmation ids). Refuse cleanly unless `JOBOT_RUN_LIVE_BROWSER=1`.
  - `linkedin`: `fill_form` returns profile-grounded email/name only,
    `submit_application` runs the Easy Apply saga, `verify_submission`
    re-checks the success marker (saga `verify_submitted`). All raise
    `NotImplementedError` unless `JOBOT_RUN_LIVE_BROWSER=1`. Injectable
    `saga_factory`/`profile_loader`/`browser_provider` for hermetic tests.
  - Pipeline behavior with live browser disabled: Naukri submit returns
    False -> phase 11 DoD fails -> application FAILED (honest, verified by
    `tests/integration/test_naukri_fixture.py`); LinkedIn raises -> FAILED.
- **Runner (T4.1)**: `src/jobot/runner.py` campaign loop runs
  `ApplyOrchestrator.apply()` (saga/idempotency/grounding) and halts when
  `router.current_spent_usd >= router.daily_budget_usd` (LLM cost gate).
- **Live tests opt-in**: `JOBOT_RUN_LIVE_BROWSER=1 pytest
  tests/integration/test_naukri_live.py tests/integration/test_linkedin_easy_apply_live.py`.
- **Test suite (release-1.0)**: pytest 318 passed / 13 skipped (13 = live
  opt-in browser tests), ruff check/format clean, mypy clean (115 files).

## Phase 6 Addendum (2026-08-15, release-2.0)

- **Workday honest adapter**: `src/jobot/adapters/workday.py` rewritten �
  `WorkdayApi` talks to the public cxs JSON API
  (`POST https://{tenant}.wd3.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
  and `/jobPosting/{jobId}`; `html.unescape` on HTML entities).
  `discover_jobs(keywords, location, limit, company)` requires a tenant /
  `company` (default from config `adapters.workday.tenant`). `WorkdaySubmitter`
  and `WorkdayVerifier` drive a real Patchright browser and refuse (honest
  failure) unless `JOBOT_RUN_LIVE_BROWSER=1`; `fill_form` returns
  profile-grounded values only, never fabricated form data. No confirmation
  IDs are ever invented. `tests/test_workday_adapter.py` (16 hermetic tests,
  FakeBrowser/FakeHTTPResponse).
- **GUI sidecar (JSON-RPC 2.0 over stdio)**: `src/jobot/gui/sidecar.py`
  `SidecarServer.handle_request` implements 22 methods: `ping`, `status`,
  `profile_info`, `list_sites`, `discover_jobs`, `apply`, `approve`,
  `applications`, `tracker_stats`, `campaign_status`, `pause`, `resume`,
  `schedule_list`, `schedule_add`, `schedule_remove`, `digest`, `doctor`,
  `config_show`, `config_get`, `config_set`, `config_unset`, `traces`.
  Line-delimited JSON on stdin/stdout; JSON-RPC error codes -32601
  (method not found), -32602 (invalid params), -32603 (internal), -32700
  (parse). Dependencies injectable for hermetic tests
  (`tests/test_sidecar.py`, 25 tests). CLI entry: `jobot sidecar`.
- **Shared doctor module**: `src/jobot/doctor.py` `run_doctor_checks() ->
  DoctorReport`; CLI `doctor_cmd` and sidecar `doctor` RPC both use it.
- **Registry consolidation**: `infer_site` moved into
  `src/jobot/adapters/registry.py`; `JobDiscoveryEngine.scraper_for()`
  public alias (mypy: jobot.stubs covers numpy/pandas).
- **Desktop GUI (Tauri 2 + React 18)**: `gui/` � `src/` (React app:
  `main.jsx`, `App.jsx`, `lib/{rpc.js,tauriTransport.js,useAsync.js}`,
  `views/{Dashboard,Discover,Apply,Controls,Settings}.jsx`, `styles.css`),
  `tests/` (vitest: 9 RPC + 7 component), `src-tauri/` (Rust shell:
  `Cargo.toml`, `src/{main,lib}.rs`, `tauri.conf.json`,
  `capabilities/default.json` � shell spawn/execute scoped to `jobot`
  sidecar only). Tauri Rust is NOT in CI gates (pytest/ruff/mypy/
  vitest/prettier only); `tauri:dev`/`tauri:build` are local-only.
  GUI deps live in the ROOT `package.json` (CI runs `npm ci` once);
  `gui/package.json` is a thin wrapper (`dev`/`build`/`tauri` scripts).
- **GUI contract tests**: `tests/npm/system.test.js` (framing) +
  `gui/tests/` (RPC client + SSR-safe views). `vitest.config.js` at root
  applies `@vitejs/plugin-react` to gui tests and includes both suites.
- **Test suite (release-2.0)**: pytest 359 passed / 13 skipped, ruff
  check/format clean, mypy clean (116 files), vitest 18 passed (3 files),
  prettier clean. `cargo check` requires a Windows C toolchain
  (MinGW `dlltool` or MSVC `link.exe`) � not present on the dev machine;
  Rust shell is minimal and not gated in CI.
