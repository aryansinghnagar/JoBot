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