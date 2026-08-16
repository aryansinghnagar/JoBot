# JoBot Master Plan

## Ultimate Autonomous Job Application Agent - Refactor, Reliability, Product, Security, Performance, and Release Program

**Document status:** Master implementation plan  
**Date:** 2026-08-15  
**Target product:** JoBot v1.0.0 and the post-v1 career operating system  
**Primary artifact:** `MASTER_PLAN.md`  
**Guiding doctrine:** `AGENTS.md`  
**Repository:** https://github.com/aryansinghnagar/JoBot

> [!IMPORTANT]
> This document is the single integrated plan for taking JoBot from its current repository state to a reliable release for an average user and then to the longer-term autonomous career operating system. It preserves the substantive ideas from `Plan1.md`, `Plan2.md`, `Plan3.md`, `plan4.md`, `plan5.md`, and `Plan1.pdf`, but it does **not** preserve their conflicting snapshots, sequencing, or assumptions. It resolves them using a strict evidence hierarchy and a dependency-first implementation order.

> [!CAUTION]
> “Autonomous” does not mean “blindly automated.” JoBot must be autonomous inside an explicit policy envelope, with durable state, risk-based approvals, evidence, verification, budget controls, and an immediately visible stop path. Platform protections must not be defeated merely to increase application volume.


> **Unified source-set note (2026-08-16):** This canonical plan incorporates the available source set found in the project library: `agents.md`, `Plan1.md`, `Plan1.pdf`, `Plan2.md`, `Plan3.md`, `plan4.md`, and `plan5.md`. Duplicate exports and earlier master-plan drafts were treated as synthesis artifacts, not independent requirements. No Plan6-Plan10 files were present in the available library at synthesis time, so no unsupported content has been invented for them.

## 0. Executive Decision

The correct strategy is **not** to rewrite JoBot and is **not** to add every attractive feature immediately. The highest-leverage path is to turn the existing architecture into a trustworthy execution substrate, prove one complete application workflow under crash/failure/restart, and then add breadth on top of that substrate.

The master sequence is:

```text
Truthful baseline
      ->
Security / supply-chain blockers
      ->
Durable execution
      ->
Application state + effect correctness
      ->
Browser and adapter reliability
      ->
Candidate truth + AI reliability
      ->
Verification / evidence / evals
      ->
Control-plane UX
      ->
Release engineering
      ->
Core capability expansion
      ->
Outcome learning
      ->
Bounded self-improvement
      ->
Multi-worker / multi-machine scale
      ->
Career operating system
```

The v1.0 product promise should be narrower and stronger than “apply everywhere”: 

> **JoBot reliably discovers, evaluates, prepares, verifies, submits, and tracks applications across a defined set of supported job sources and ATSs, while preserving durable state, respecting explicit policies, surviving crashes, grounding candidate facts, capturing evidence, and exposing every consequential action to the user.**

The long-term moat is the combination of:

**durable execution + trustworthy candidate data + evidence + human-governed autonomy + outcome learning + career intelligence.**

## 1. Evidence Hierarchy and Conflict Resolution

This plan combines multiple sources with different ages and purposes. To prevent architectural drift, every implementation decision follows this precedence:

| Rank | Source | Rule |
|---|---|---|
| 1 | `AGENTS.md` | Governing engineering doctrine and non-negotiable safety/reliability principles |
| 2 | Current repository state at the release target commit | Ground truth for what actually exists, passes, or fails |
| 3 | Current code contracts and tests | Source of behavioral truth for existing interfaces |
| 4 | This Master Plan | Integrated target architecture and implementation sequence |
| 5 | User-supplied Plan1-5 documents | Requirements, ideas, risks, and architectural evidence retained here |
| 6 | External research and ecosystem references | Inspiration and hypotheses; never adopted without local validation |
| 7 | Historical docs, old worklogs, old snapshots | Context only; never proof of current capability |

### 1.1 Snapshot claims are not release facts

Several supplied plans contain different snapshots of JoBot, including conflicting test counts, version numbers, adapter counts, and statements such as “release 2.0 tagged.” The current GitHub `main` branch still contains version drift (`pyproject.toml` 0.1.0, root package 0.1.0, GUI package/Tauri metadata 2.0.0), and the current CI workflows still use older frontend/toolchain choices. Therefore:

1. Every phase begins with a machine-generated baseline report.
2. Every release note describes only what was verified at the release commit.
3. Historical claims are preserved as planning evidence, not copied into user-facing documentation.
4. No “implemented” feature is considered complete without a test, observable behavior, or a documented external validation result.

### 1.2 Current repo facts confirmed during this audit

The live repository confirms at minimum:

- public repository on `main` with a dual Python/Tauri architecture;
- `AGENTS.md` at the root and a second agent-instruction artifact under `.agents/`;
- root `README.md` is still very small and refers to an older Merge Plan as authoritative;
- `pyproject.toml` declares version `0.1.0`, Python `>=3.11`, SPDX-style intent but legacy TOML license syntax, and mypy configured for Python 3.12;
- root `package.json` declares version `0.1.0` and uses Vite 5 / Vitest 3 / Node 18-20 in CI;
- `gui/package.json` declares version `2.0.0`;
- `tauri.conf.json` declares version `2.0.0`, `csp: null`, and only a placeholder-style icon list;
- Tauri shell permissions currently allow unrestricted arguments for the `jobot` command;
- CI runs on `main` and `dev`, uses older Action tag references, uses a narrow Ruff selection, and lacks the full security/test/release gates described by the plans;
- the PyPI workflow still uses a long-lived API token rather than OIDC Trusted Publishing;
- Dependabot currently covers pip, npm, and GitHub Actions but not cargo;
- the repo root contains multiple historical planning artifacts that must be rationalized after this Master Plan becomes authoritative.

These observations are consistent with the most important risks identified in the supplied plans, but all individual implementation tasks still require fresh verification at execution time.

## 2. Product North Star and Operating Invariants

JoBot must evolve from a collection of job-search utilities into a **career execution operating system** with one user-facing control surface and a reliable internal execution fabric.

### 2.1 Closed loop

```text
goal
 -> decomposition
 -> explicit task graph
 -> policy evaluation
 -> execution
 -> verification
 -> evidence
 -> durable state update
 -> memory update
 -> visible result
 -> learning signal
 -> improvement candidate
```

### 2.2 Core production invariants

These invariants are mandatory across all implementation phases:

```text
NO ACTION WITHOUT A STATE
NO STATE WITHOUT AN EVENT
NO COMPLETION WITHOUT VERIFICATION
NO SIDE EFFECT WITHOUT POLICY
NO RETRY WITHOUT IDEMPOTENCY
NO LONG RUN WITHOUT CHECKPOINT
NO MEMORY WITHOUT PROVENANCE
NO AUTONOMY WITHOUT MEASUREMENT
NO EXTERNAL CONTENT IS TRUSTED BY DEFAULT
NO AMBIGUOUS EFFECT IS REPLAYED BLINDLY
NO SECURITY GATE MAY BE BYPASSED FOR VELOCITY
```

### 2.3 Autonomy model

Autonomy is not one global switch. It is a function of action, target, reversibility, credential sensitivity, external side effect, personal data, cost, volume, model confidence, historical success, site health, and trust.

Recommended action tiers:

| Tier | Example | Default |
|---|---|---|
| R0 | Local read / local analysis | Automatic |
| R1 | Public job discovery | Automatic |
| R2 | Resume generation, scoring, draft creation | Automatic with validation |
| R3 | Application preparation / draft form fill | Automatic or draft-only |
| R4 | Save / bookmark / tracker mutation | Policy dependent |
| R5 | Submit an application | Human approval initially; bounded autonomy only after proven trust |
| R6 | Recruiter outreach / message send | Approval by default |
| R7 | Credential or security-setting changes | Human approval |
| R8 | Irreversible or high-impact actions | Human only |

Trust is scoped at least by user + domain/site + adapter + skill + action class. Promotion is earned from measured outcomes, not a hard-coded number of successes alone.

## 3. Priority System

### P0 - release-critical

Everything required to make the core workflow reliable, safe, testable, supportable, and shippable for an average user.

P0 includes:

- truthful baseline and repository freeze;
- security vulnerabilities and code-scanning issues that affect the release path;
- supply-chain controls;
- secrets/vault hardening;
- durable task state, atomic leasing, leases, attempts, checkpoints, events, recovery, quarantine;
- explicit application state machine, effect ledger, idempotency, reconciliation, unknown states;
- durable human approval;
- candidate truth and grounded question answering;
- browser/session reliability and evidence;
- independent verification;
- failure injection and recovery tests;
- release-grade backups/migrations/doctor;
- essential GUI control-plane views;
- version/source-of-truth cleanup;
- installability and release artifacts;
- complete user documentation;
- cleanup and refactor of known high-risk technical debt.

### P1 - product-completing and high-leverage

- multi-profile support;
- resume PDF ingestion;
- LLM streaming;
- direct ATS API application paths where officially supported;
- broader ATS families;
- screening answer bank and autofill improvements;
- Kanban tracker/funnel analytics;
- data export/import;
- apply-method classification;
- job clipping;
- follow-up scheduling and email sync;
- improved matching and recommendation;
- OpenTelemetry and optional external trace/eval exports;
- MCP interface;
- TUI / HTML reports where useful;
- local-model support (including vision paths) where quality is adequate;
- proactive scheduled discovery and opportunity digests;
- resume variants and outcome reporting.

### P2 - strategic moat / opt-in / experimental

- browser extension;
- bulk campaigns with strict caps and compliance controls;
- networking graph and referral intelligence;
- LinkedIn profile scoring;
- multilingual resumes and region-specific templates;
- salary negotiation toolkit and advanced market intelligence;
- plugin gallery;
- skill extraction from successful trajectories;
- automatic eval generation;
- bounded self-improvement;
- temporal career graph;
- multi-machine workers and remote sandboxes;
- advanced browser skill registry;
- experimental apply automation for platforms where user authorization and platform terms permit it.

### P3 - future general agent platform

The broader `AGENTS.md` vision remains a strategic north star: general-purpose computer work, broader business operations, science workflows, desktop automation, email/calendar/CRM, project/company operations, and cross-workspace intelligence. These capabilities must reuse JoBot's durable runtime rather than create a second orchestration architecture.

## 4. Phase 0 - Truth, Baseline, and Freeze

**Priority:** P0  
**Goal:** establish a measurable starting point before changing architecture.

### 4.1 Inventory

Produce a generated baseline covering:

- Python source files, tests, GUI source, Rust source, workflows, scripts, docs, config, artifacts;
- dependency graph and optional dependency graph;
- lines/bytes for large files;
- public CLI commands and JSON-RPC methods;
- adapter registry and adapter capabilities;
- state-machine states and transitions;
- database schema and migrations;
- task/saga/checkpoint capabilities;
- model providers and provider features;
- browser capabilities and session lifecycle;
- memory tiers actually wired vs merely documented;
- telemetry and logging paths;
- current coverage, test counts, skip reasons, execution time;
- current CI workflow behavior;
- package and GUI version sources;
- security alerts, SAST/DAST findings, dependency advisories;
- repo files that are stale, duplicated, generated, historical, or apparently unused.

### 4.2 Baseline scorecard

Create `docs/quality/production-readiness.md` with a 0-10 score per subsystem, evidence links, confidence, known gaps, and next gate. Use measurable fields rather than subjective “looks production-ready” language.

### 4.3 Performance baseline

Measure:

- CLI cold start;
- GUI cold start and sidecar start;
- database startup and first query;
- job discovery throughput and latency;
- parse/normalize/deduplicate cost;
- match scoring latency;
- LLM call latency, token count, and cost;
- resume generation latency;
- PDF compilation/extraction/ATS verification latency;
- browser session startup/reuse cost;
- form-fill throughput;
- sidecar RPC p50/p95/p99;
- peak RSS and steady-state RSS for CLI, sidecar, browser, and GUI;
- CPU utilization during batch operations;
- SQLite file/WAL growth;
- artifact storage growth;
- restart/recovery time.

### 4.4 Freeze rules

During Phase 0, only P0 fixes, security fixes, baseline instrumentation, and changes required to unlock the plan are permitted. No feature expansion that changes product scope.

**Exit gate:** baseline report committed; all contradictory plan claims are tagged as historical; release blockers and P0 work items are enumerated in machine-readable form.

## 5. Phase 1 - Security, Supply Chain, and Repository Hygiene

**Priority:** P0  
**Primary inputs:** plan5 + plan4 + Plan1 security sections  
**Goal:** remove release-blocking security and operational debt before deep architectural refactors.

### 5.1 Frontend dependency security

- Move from vulnerable Vite 5-era dependency ranges to the current supported Vite 8.x line after compatibility testing; Plan5's `8.2.1` becomes the candidate baseline rather than an unquestioned permanent pin.
- Upgrade Vitest and the React/Vite integration consistently.
- Require Node.js versions compatible with the selected Vite release; current Vite 8 documentation requires Node 20.19+ or 22.12+.
- Re-run `npm audit`, lockfile verification, tests, and GUI build.
- Add dependency policy to reject known high/critical vulnerabilities unless explicitly risk-accepted.

### 5.2 URL and site inference security

Replace substring-based host classification with URL parsing and exact/controlled suffix matching. Unknown hosts must raise a clear error rather than silently defaulting to a known adapter.

Adversarial tests must cover:

- attacker-controlled lookalike subdomains;
- query strings containing trusted domains;
- username/password URL fields;
- ports;
- uppercase/lowercase variants;
- trailing dots and slashes;
- scheme-less input;
- IDN/punycode edge cases;
- redirect chains;
- user-provided company strings that resemble domain names.

### 5.3 Tauri security

- Replace `csp: null` with a restrictive policy appropriate to the GUI's actual network and IPC needs.
- Replace unrestricted `args: true` with narrow allowlists for sidecar invocation.
- Explicitly define window capability scope.
- Review every Tauri permission with deny-by-default assumptions.
- Audit shell spawn/execute, filesystem, opener, HTTP, dialog, process, and updater capabilities.
- Add capability regression tests so future GUI features cannot silently broaden permissions.

### 5.4 Vault hardening

- Create keyfiles atomically with restrictive permissions.
- Refuse unsafe ownership or permissions on POSIX.
- Use `O_NOFOLLOW` where available.
- Document Windows ACL reliance and test the expected security posture.
- Rotate/repair any keyfile fallback behavior that can expose secrets during creation.
- Ensure secrets never appear in events, logs, prompts, crash payloads, traces, screenshots, or serialized task arguments.

### 5.5 CI hardening

- SHA-pin GitHub Actions.
- Keep workflow permissions minimal.
- Add `pip-audit`, `npm audit`, `gitleaks`, `actionlint`, and cargo auditing when Rust builds are present.
- Add Rust to CodeQL once the Tauri component is considered release-critical.
- Remove or fix stale `dev` branch triggers.
- Broaden Ruff to the intended project configuration rather than the current narrow E/F subset.
- Pin CI tool versions or use a locked tool environment to prevent unreviewed CI drift.
- Add import smoke tests against the base install to detect undeclared runtime dependencies.
- Require security jobs to complete before release tags.

### 5.6 Supply chain and provenance

- Generate Python and Node SBOMs and, once the desktop release is included, a Rust-aware SBOM.
- Attest build provenance for wheels, containers, and desktop artifacts.
- Make artifact verification part of release verification.
- Use reproducible build inputs where practical.
- Record exact source commit, toolchain version, OS runner, dependency lock state, and artifact digest.

GitHub's artifact attestation system is designed for build provenance and supports verification via GitHub CLI. Use it for all release artifacts, not only SBOMs. [GitHub artifact attestation documentation](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations)

### 5.7 PyPI publishing

Replace API-token publishing with PyPI Trusted Publishing via GitHub OIDC and a protected PyPI environment. PyPI explicitly documents Trusted Publishing as the preferred short-lived-credential approach for CI. [PyPI Trusted Publishing documentation](https://docs.pypi.org/trusted-publishers/)

### 5.8 Repo hygiene before feature growth

- Reconcile `queues/improve.md` and all momentum queues with the actual code.
- Remove stale claims that name already-wired subsystems as unwired.
- Create a generated dependency and file inventory so cleanup can be repeated safely.
- Remove secrets, caches, build outputs, local browser profiles, logs, coverage outputs, and temporary artifacts from version control if discovered.

**Exit gate:** no unaccepted release-blocking security issue; secure Tauri capability model; exact URL validation; hardened vault; CI security jobs green; provenance pipeline demonstrably working.

## 6. Phase 2 - Durable Execution and Control Plane Foundation

**Priority:** P0  
**Primary inputs:** Plan1 durable execution, `AGENTS.md` task system doctrine  
**Goal:** make long-running work safe to interrupt, inspect, resume, cancel, retry, quarantine, and reconcile.

### 6.1 Persistent task model

Create first-class entities:

- `Goal`
- `Task`
- `TaskAttempt`
- `TaskLease`
- `TaskDependency`
- `TaskEvent`
- `TaskArtifact`
- `ApprovalRequest`
- `ExternalEffect`
- `Checkpoint`
- `Incident`
- `BudgetReservation`

Each task must persist at least: goal, project/profile, scope, skill tags, priority, risk, owner, reviewer, dependencies, status, budget, attempt count, deadlines, verification plan, evidence references, artifact references, error class, timestamps, and next action.

### 6.2 State machine

Canonical task states:

```text
PENDING -> READY -> CLAIMED -> RUNNING
                      |            |
                      |            +-> WAITING
                      |            +-> VERIFYING
                      |            +-> RETRYING
                      |            +-> COMPLETED
                      |            +-> FAILED
                      |            +-> UNKNOWN
                      |            +-> QUARANTINED
                      |            +-> CANCELLED
```

Application states must be separate from task states.

### 6.3 Atomic worker claiming

Use database transactions/conditional updates so two workers can never own the same task lease. Leases expire and are recoverable. Workers emit heartbeats. A dead worker must not strand work indefinitely.

### 6.4 Pull-based workers

Follow the `AGENTS.md` recommendation:

- workers poll for eligible work;
- filter by capability/permission;
- atomically claim;
- checkpoint before meaningful external actions;
- execute;
- verify;
- commit result/event/evidence;
- release or renew lease;
- leave explicit handoff state.

### 6.5 Durable waits

Waiting is not an error. Support durable waitpoints for:

- user approval;
- missing profile information;
- browser CAPTCHA/human handoff;
- rate-limit recovery;
- scheduled execution;
- email/webhook events;
- provider recovery;
- job expiration/reconciliation.

### 6.6 Events

Introduce an append-only event ledger with event versioning, correlation ID, causation ID, actor, timestamp, and payload schema. Events must power:

- audit history;
- task timelines;
- UI activity feeds;
- incident diagnosis;
- replay tooling;
- analytics;
- eval trajectory capture.

### 6.7 Quarantine and dead-letter behavior

Repeatedly failing or suspicious work is moved to quarantine with full evidence rather than endlessly retried. Recovery requires a deliberate strategy or human action.

### 6.8 Cancellation

Cancellation must be cooperative and durable. Define what cancellation means for each action class, including whether external effects are already committed.

**Exit gate:** deliberately kill a worker during every major phase and prove that the run resumes without losing state or duplicating work.

## 7. Phase 3 - Application State, Effect Ledger, Idempotency, and Verification

**Priority:** P0  
**Goal:** eliminate the most dangerous class of job-automation failure: uncertainty around external side effects.

### 7.1 Explicit application state machine

Use a formal application protocol with entry/exit guards. A representative flow is:

```text
DISCOVERED
 -> NORMALIZED
 -> DEDUPLICATED
 -> ENRICHED
 -> MATCHED
 -> SHORTLISTED
 -> PREPARING
 -> PREPARED
 -> AWAITING_APPROVAL
 -> SUBMITTING
 -> SUBMISSION_UNKNOWN | SUBMITTED
 -> VERIFYING
 -> VERIFIED | VERIFICATION_UNKNOWN
 -> OUTCOME_TRACKING
 -> INTERVIEW | REJECTED | OFFER | WITHDRAWN | EXPIRED
```

### 7.2 Effect ledger

Every side effect gets a durable `ExternalEffect` record:

```text
effect_id
application_id
task_id
effect_type
idempotency_key
request_hash
started_at
completed_at
status
external_reference
verification_state
compensation_state
replay_policy
```

### 7.3 Idempotency rules

Every externally mutating operation gets a deterministic or persisted idempotency key. The effect layer must answer “was this exact effect already attempted?” before retrying.

For irreversible actions:

```text
ambiguous local state
 -> reconcile external system
 -> if verified, record committed effect
 -> if unresolvable, quarantine
 -> never blindly replay
```

### 7.4 Submission verification

Never equate clicking Submit with success. The verification pipeline must attempt to detect:

- explicit confirmation message;
- confirmation/application ID;
- redirect or thank-you page;
- external tracker state;
- submission email where available;
- screenshot evidence;
- portal-specific verification artifacts.

Ambiguity becomes `SUBMISSION_UNKNOWN`, not `SUBMITTED`.

### 7.5 Approval model

Approval requests are durable entities shared by CLI, GUI, sidecar, and later MCP.

Approval screen/card must show:

- what will happen;
- why it is needed;
- target site/job/company;
- exact data being submitted;
- risk tier;
- candidate-fact provenance;
- generated artifacts;
- estimated cost;
- what happens after approval;
- whether editing is allowed;
- expiration time;
- approve / edit / reject / defer.

### 7.6 Compensation

Where a reversible action can be undone, encode the compensating action. Where it cannot, encode quarantine/reconciliation instead. Do not pretend local bookkeeping is compensation for an irreversible external action.

**Exit gate:** no integration test can produce two submissions for the same idempotency key; interrupted applications reconcile correctly; all consequential actions emit evidence and an event.

## 8. Phase 4 - Browser Reliability and Adapter Platform

**Priority:** P0  
**Primary inputs:** Plan1 browser subsystem, Plan3 AR-1/AR-2/AR-3/AR-4/AR-5, plan2 browser work  
**Goal:** browser automation becomes a first-class reliability subsystem rather than a collection of adapter-specific scripts.

### 8.1 BrowserSessionManager

Introduce explicit lifecycle ownership for:

- browser pool;
- browser process;
- persistent profiles;
- session persistence;
- navigation;
- named actions;
- selector registry;
- selector healing;
- screenshot capture;
- DOM/form snapshots;
- rate-limit detection;
- site-health state;
- human takeover;
- cleanup and recovery.

### 8.2 Named actions

Prefer actions such as `open_application_form`, `select_location`, `upload_resume`, `answer_question`, `review_before_submit`, and `detect_confirmation` over arbitrary DOM manipulation. Each action has typed inputs, expected outputs, verification, timeout, and evidence requirements.

### 8.3 Selector registry and healing

Centralize selector definitions by site and workflow step. Use ordered candidate locators and observable health metrics. Healing means controlled fallback to known alternatives and recording the drift; it does not mean unrestricted AI invention of arbitrary selectors without verification.

### 8.4 Browser evidence

Every risky action should capture, as appropriate:

- pre-action screenshot;
- relevant DOM/form state;
- action name and arguments;
- post-action screenshot;
- result;
- verification result;
- trace ID;
- application ID.

### 8.5 Blocking and compliance boundary

Site blocking is a state transition:

```text
SITE_BLOCKED
 -> circuit breaker
 -> incident
 -> quarantine
 -> alternate supported source or human action
```

Do **not** build a release-critical strategy around defeating platform anti-automation controls.

For example, LinkedIn's current User Agreement explicitly prohibits scraping and unauthorized automated methods, as well as circumventing access controls and use limits. Therefore LinkedIn automation must be an explicitly governed, opt-in, policy-enforced capability and not the reason to weaken the core safety model. [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)

The plan's older “anti-detection” ideas are reinterpreted as **browser reliability and realistic interaction only where permitted**, not as a mechanism to circumvent platform security or policy enforcement.

### 8.6 Adapter family generalization

Extract reusable HTTP/JSON patterns where multiple ATSs share a protocol shape. Plan3's CXS-family direction should become a reusable adapter base plus site-specific configuration.

Candidate initial family expansion:

- Workable;
- Recruitee;
- Teamtailor;
- BambooHR;
- other public career-page JSON feeds discovered and verified.

### 8.7 Boundary schemas

All adapter inputs and outputs are validated with Pydantic models. Invalid results move to quarantine instead of being silently coerced.

Required canonical types include:

- `JobPosting`
- `Company`
- `ApplicationQuestion`
- `CandidateAnswer`
- `ApplicationRequest`
- `ApplicationResult`
- `VerificationResult`
- `SiteHealth`

### 8.8 Apply-method classification

Every discovered posting should be classified as:

- API-capable;
- browser form;
- browser-assisted/manual;
- email application;
- external redirect;
- unknown.

The method is visible before application preparation and can be overridden by policy.

**Exit gate:** mock ATS and all Tier-1 supported sites survive injected timeouts, browser crashes, navigation failures, stale selectors, malformed responses, and interrupted sessions without silent corruption.

## 9. Phase 5 - Candidate Truth, AI Reliability, Matching, and Document Pipeline

**Priority:** P0 core, then P1 expansion  
**Goal:** make AI outputs useful without allowing the model to invent candidate facts or silently change durable truth.

### 9.1 Candidate Truth System

Create a canonical candidate fact layer.

Representative fields:

```text
fact_id
category
value
source
source_artifact
confidence
valid_from
valid_to
last_verified_at
profile_version
```

Sources can include:

- imported resume;
- user-entered facts;
- verified application data;
- authenticated recruiter/contact records;
- user corrections.

The model may **propose** a fact or transformation but must not silently create a material credential.

### 9.2 Application question answering

Classifier:

```text
FACTUAL
PREFERENCE
ELIGIBILITY
LEGAL
SENSITIVE
FREE_TEXT
UNKNOWN
```

Routing:

```text
question
 -> classifier
 -> known fact?
    -> yes: grounded answer
    -> no: policy check
             -> model proposal
             -> grounding verifier
             -> approval if necessary
```

Questions involving legal status, immigration, disability, medical information, demographic/EEO choices, criminal history, employment authorization, or other sensitive material should have explicit policy boundaries and often default to user confirmation.

### 9.3 Multi-stage job matching

Avoid spending an expensive model call on every posting:

1. deterministic filter: location, visa/work authorization, employment type, compensation, seniority, title;
2. lexical/embedding similarity;
3. structured LLM evaluation;
4. deep company/job research for shortlisted roles;
5. recommendation with explanation and evidence.

Store match components rather than only one opaque score.

### 9.4 Match explanation

For every recommendation, show why the job matched:

- skill overlap;
- required vs achieved experience;
- location/work mode;
- compensation fit;
- industry/domain fit;
- evidence-backed gaps;
- confidence and uncertainty.

### 9.5 Job quality and fraud detection

Score job risk for:

- company legitimacy;
- domain mismatch;
- salary anomalies;
- duplicate/reposted jobs;
- recruiter authenticity;
- application-domain mismatch;
- suspicious payment requests;
- credential requests;
- malicious instructions;
- prompt injection;
- suspicious attachments/links.

Treat job descriptions, web pages, emails, and recruiter-supplied documents as **untrusted external content**. OWASP's 2025 guidance continues to identify prompt injection as a distinct LLM security risk, including attacks that cause untrusted content to influence tools or decisions. [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

### 9.6 Resume/document pipeline

Target pipeline:

```text
Job Description
 -> structured parser
 -> fit evaluation
 -> candidate facts
 -> tailoring plan
 -> draft
 -> independent reviewer
 -> revision
 -> PDF compilation
 -> PDF text extraction
 -> ATS verification
 -> visual verification
 -> artifact manifest
```

The reviewer must detect:

- unsupported claims;
- keyword stuffing;
- contradictions;
- missing critical requirements;
- broken formatting;
- malformed sections;
- illegal or misleading claims.

### 9.7 PDF ingestion

Add resume ingestion from PDF using a deterministic parser first, with LLM extraction only for ambiguous fields. Require user confirmation before saving the imported profile.

Target command:

```text
jobot profile import-resume <path>
```

### 9.8 LLM streaming

De-stub the provider streaming interfaces across all supported providers and OpenAI-compatible backends. The router must expose a common streaming API and surface provider failure as a normal fallback decision.

Streaming should be used for interactive UX but never become a durability dependency: long-running work must be checkpointed independent of whether the UI is connected.

### 9.9 Prompt registry

Version prompts like code:

```text
prompts/
  application/
    fit_evaluation/
    resume_tailoring/
    cover_letter/
    question_answering/
    interview/
```

Every call stores prompt ID/version, model, provider, temperature/config, schema version, tool version, profile version, and policy version.

### 9.10 ModelRouter v2

Persist:

- model capabilities;
- provider health;
- routing decisions;
- token usage;
- cost;
- budget reservations;
- task quality outcomes;
- fallback events.

Route using:

```text
capability + quality + cost + latency + availability + historical success
```

not fixed provider ordering.

### 9.11 Economics

Use cheap models for classification, extraction, formatting, and summarization; stronger models for difficult planning, verification, reasoning, and adversarial review. Add task-local budgets and a hard ceiling at goal/project level.

**Exit gate:** critical evals produce no unsupported candidate claims; PDF artifacts pass both text-layer and visual checks; model failures degrade without corrupting task state.

## 10. Phase 6 - Multi-Profile, Job Data, and Career Domain Model

**Priority:** P1  
**Goal:** make JoBot a real product for users with multiple job targets and long-running searches.

### 10.1 Profiles

Support named profiles, for example:

```text
backend-senior
ml-research
product-engineering
india-fulltime
remote-international
```

Persist profile ID through tasks, checkpoints, applications, documents, memory, and outcomes. Provide CLI/GUI import/export and safe switching.

### 10.2 Job entity model

Normalize job records across all sources:

- canonical job ID;
- source and source ID;
- company ID;
- title;
- location(s);
- remote/hybrid/on-site;
- employment type;
- salary/benefits;
- seniority;
- visa/sponsorship metadata;
- skills;
- description;
- application method;
- posting timestamp;
- last-seen timestamp;
- expiry/freshness status;
- dedupe fingerprint;
- source URL;
- raw source artifact hash.

### 10.3 Company normalization

Canonicalize aliases and domains into one company entity, with optional relationships for subsidiaries, parent companies, recruiters, locations, and jobs.

### 10.4 Discovery

Integrate JobSpy and other compatible sources behind JoBot's adapter layer rather than embedding a scraper as the architecture. Keep each source replaceable and health-monitored.

### 10.5 Deduplication

Use deterministic fingerprints plus semantic similarity when necessary. Never merge distinct jobs solely because titles are similar.

### 10.6 Job freshness

Implement stale/expired detection, last-seen timestamps, 404/410 handling, portal changes, and dedupe against prior campaigns.

## 11. Phase 7 - Core Product UX and Control Plane

**Priority:** P0/P1  
**Goal:** make the system understandable to a non-expert while keeping deep controls available.

The UI is part of JoBot's intelligence. The same task/state/evidence model must power CLI, GUI, future TUI, APIs, and MCP.

### 11.1 Universal ask surface

The user should be able to type or paste:

- job URLs;
- files;
- constraints;
- natural-language goals;
- schedules;
- budgets;
- risk tolerance;
- approval preferences.

The system infers whether the request is an answer, one-time task, plan, workflow, recurring automation, monitoring task, or long-running goal. Ambiguity should trigger one targeted clarification rather than a questionnaire.

### 11.2 Home / command center

Display:

- active work;
- pending approvals;
- failures/incidents;
- daily/weekly application totals;
- costs;
- top matches;
- stale/stuck work;
- next action.

### 11.3 Universal inbox

One place for:

- approvals;
- questions for the user;
- failures;
- incidents;
- recommendations;
- recruiter signals;
- follow-up reminders.

### 11.4 Job board / discovery view

Provide:

- sortable/filterable jobs;
- match score and explanation;
- compensation and location filters;
- freshness;
- apply method;
- fraud/quality score;
- shortlist/save/reject;
- clip arbitrary jobs from URLs.

### 11.5 Application detail

Show:

- job/company;
- fit score;
- selected profile;
- resume and cover-letter artifacts;
- screening answers;
- application state;
- approval state;
- external effects;
- screenshots;
- verification results;
- trace/timeline;
- retries;
- next action.

### 11.6 Kanban and funnel analytics

Ship the market-proven workflow visualization:

```text
Discovered -> Shortlisted -> Prepared -> Applied -> Responded -> Interview -> Offer / Rejected
```

Funnel metrics include stage counts, conversion rates, time-in-stage, by source, company, role, profile, and resume variant.

### 11.7 Evidence viewer

Users can inspect screenshots, form snapshots, PDFs, extracted text, confirmation IDs, and trace events without searching disk directories.

### 11.8 Incident view

Display:

- what happened;
- timeline;
- affected applications;
- root cause hypothesis;
- evidence;
- mitigation;
- current state;
- recommended next action;
- whether user approval is needed.

### 11.9 Settings

Include:

- providers;
- profiles;
- adapter enablement;
- application policies;
- caps and budgets;
- browser profiles;
- data retention;
- backup/restore;
- telemetry consent;
- update channel;
- trust controls.

### 11.10 Accessibility

Add explicit requirements omitted by several supplied plans:

- keyboard navigation;
- semantic labels;
- focus management;
- sufficient contrast;
- reduced-motion support;
- screen-reader compatibility for critical workflows;
- clear error text;
- non-color-only status signals.

**Exit gate:** a new user can install, run `jobot doctor`, import a resume, add a job target, discover jobs, prepare one application, review evidence, and understand what JoBot is waiting for without reading source code.

## 12. Phase 8 - Observability, Evals, and Learning

**Priority:** P0  
**Goal:** make quality measurable and self-improvement evidence-based.

### 12.1 Structured telemetry

Use structured JSON logs locally. Add OpenTelemetry instrumentation as the vendor-neutral trace/metric layer. OpenTelemetry provides standard APIs and SDKs for traces, metrics, and logs. [OpenTelemetry documentation](https://opentelemetry.io/docs/)

Trace hierarchy:

```text
Goal
  -> Task
      -> Model call
      -> Tool call
      -> Browser action
      -> Policy evaluation
      -> Approval
      -> Verification
      -> Artifact
      -> External effect
```

Every trace carries stable identifiers, provider/model, prompt version, policy version, adapter version, worker, profile, and application ID.

### 12.2 Metrics

At minimum:

- task success and verification rate;
- median and p95 completion time;
- cost per successful application;
- intervention rate;
- retry rate;
- quarantine rate;
- browser failure rate;
- provider fallback rate;
- application verification rate;
- unsupported-claim rate;
- match precision at useful thresholds;
- resume review failure rate;
- duplicate-effect rate (must be zero for release);
- recovery success after injected crashes;
- memory reuse rate;
- proactive goal generation rate;
- regression rate.

### 12.3 Evaluation suites

Required suites:

**Capability:** discovery, parsing, matching, tailoring, question answering, form filling, submission, verification, tracking.  
**Reliability:** crash/restart, network loss, timeouts, stale selectors, rate limits, browser process death.  
**Safety:** prompt injection, malicious job descriptions, secret leakage, unsafe URLs, plugin capability escalation.  
**Truthfulness:** fabricated credentials, contradictions, unsupported salary/skill claims.  
**Long horizon:** multi-stage campaign and recovery.  
**Regression:** every change against prior baseline.  
**Production-derived:** real incidents and human corrections converted into eval cases.

### 12.4 Eval release gates

A release must show:

- pass@1 where applicable;
- repeated-trial pass rate;
- cost-to-pass;
- time-to-pass;
- intervention frequency;
- silent failure rate;
- regression delta.

No “improved” claim is allowed without an eval or production measurement.

### 12.5 Trajectory recorder

Persist structured trajectories without storing chain-of-thought. Record operational decisions, tool calls, state transitions, validations, evidence, outputs, and concise rationales.

### 12.6 Outcome learning

Track:

```text
job
application
profile
resume variant
cover-letter style
match components
application source
timing
networking/referral source
interview
offer/rejection
```

Then answer questions such as:

- which roles produce interviews;
- which companies respond;
- which resume variants perform;
- which sources produce qualified opportunities;
- which skills correlate with outcomes;
- where the funnel leaks.

Use sample-size thresholds, confidence intervals, and uncertainty. Do **not** turn correlations into causal claims from small observational datasets.

### 12.7 Active-learning loop

Repeated human corrections, failures, stale assumptions, and KPI drops should generate candidate work in:

- `improve` queue;
- new eval cases;
- skill updates;
- policy updates;
- tool improvements;
- memory corrections;
- dashboard changes.

## 13. Phase 9 - Bounded Self-Improvement and Skill Extraction

**Priority:** P2 strategic, with a small P0/P1 infrastructure slice  
**Goal:** make JoBot progressively better without allowing unrestricted production self-modification.

### 13.1 Improvement loop

```text
failure / opportunity signal
 -> classify gap
    (skill / tool / policy / prompt / memory / decomposition / verifier / routing)
 -> bounded proposal
 -> isolated branch or sandbox
 -> targeted eval
 -> baseline comparison
 -> security/policy gate
 -> promote or discard
```

### 13.2 One-change rule

Prefer one bounded change, one representative eval slice, one decision. Large prompt rewrites or broad architecture changes are prohibited from being auto-promoted without staged validation.

### 13.3 Skill extraction

Convert successful trajectories into reusable skills only after review/eval:

```text
trajectory
 -> generalize
 -> skill candidate
 -> test corpus
 -> review
 -> registry
```

A browser/application skill can capture:

- navigation;
- known fields;
- question classes;
- selector candidates;
- failure modes;
- recovery strategies;
- verification rules.

### 13.4 Skill registry

Each skill defines:

- trigger;
- required inputs;
- allowed tools;
- permissions;
- expected outputs;
- state changes;
- verification;
- retry policy;
- stop conditions;
- eval corpus;
- trust level;
- version.

### 13.5 Governance of self-change

Automatic improvement must be forbidden for:

- security policy;
- credential access policy;
- destructive action rules;
- release workflow permissions;
- autonomy thresholds;
- secret storage;
- external data sharing policy.

Those changes require explicit human approval.

## 14. Phase 10 - Advanced Job-Search Capabilities

**Priority:** P1/P2 after the core loop is stable.

### 14.1 Direct ATS API paths

Where an ATS provides an official application API and the credentials/authorization model permits the intended applicant workflow, prefer the deterministic API path over browser automation.

Greenhouse documents public job-board GET endpoints and a protected application submission endpoint; the submission endpoint requires credentials appropriate to the organization's API configuration. [Greenhouse Job Board API](https://developers.greenhouse.io/job-board/)

Lever similarly documents a postings API and a posting application endpoint, including application-question retrieval and multipart uploads. [Lever Developer API](https://hire.lever.co/developer/documentation)

Implementation rule:

```text
official supported API
    > deterministic browser flow
    > human-assisted/manual flow
    > unsupported flow
```

Never infer that a public job-board read API implies authorization to submit through it.

Candidate adapters to evaluate:

- Greenhouse;
- Lever;
- Ashby;
- SmartRecruiters;
- later ATSs with stable, permitted interfaces.

### 14.2 Screening answer bank

Persist answers by normalized question hash, semantic class, source, confidence, and profile. Reuse deterministic known answers before calling an LLM.

### 14.3 Proactive discovery agent

Configurable scheduler:

- scan sources;
- normalize/dedupe;
- rank;
- alert on high-match jobs;
- optionally precompute tailored materials;
- send weekly opportunity digest.

### 14.4 Follow-up automation

Create grounded, rate-limited follow-up drafts. Separate recruiter email follow-ups from platform-native outreach. Default to human approval for sending external communications.

### 14.5 Email synchronization

Support OAuth/IMAP where practical, with local token encryption, minimal scopes, event provenance, and user-controlled retention. Parse recruiter messages into structured signals with a verifier and confidence score.

### 14.6 Interview preparation

Expand the existing interview engine with:

- role-specific question generation;
- STAR coaching;
- company research;
- skills-gap questions;
- mock interview sessions;
- evaluation rubrics;
- session memory.

### 14.7 Networking graph

Track:

- contacts;
- companies;
- recruiter/hiring-manager relationships;
- referral provenance;
- message history;
- follow-up dates.

Recommend warm introductions based on user-approved network data. Do not scrape private contacts without authorization.

### 14.8 Salary and market intelligence

Include compensation bands, geographic adjustments, role-level data, skill demand, sponsorship trends, and market signals. Keep source date/freshness and uncertainty visible.

### 14.9 Resume A/B testing

Track variant-to-application assignment, response/interview outcome, and confidence intervals. Auto-promotion should require a minimum sample size and statistically meaningful improvement, not a fixed small-N threshold.

### 14.10 LinkedIn profile analysis

Score profile quality against target roles using user-provided/exported data, not unauthorized scraping. Provide actionable improvements.

### 14.11 Multilingual resumes

Support regional resume conventions and translation with terminology preservation, profile truth gates, and locale-aware validation.

## 15. Phase 11 - MCP, API, TUI, Browser Extension, and Integration Surfaces

**Priority:** P1/P2, not part of the core durability path  
**Goal:** expose the same durable capabilities through multiple interfaces without forking business logic.

### 15.1 MCP server

Implement `jobot mcp` as an adapter over the existing control plane/sidecar APIs. The core model must not depend on MCP.

Potential tools:

- `search_jobs`
- `get_job`
- `rank_jobs`
- `get_candidate_profile`
- `generate_resume`
- `get_application`
- `prepare_application`
- `request_application_approval`
- `get_application_evidence`
- `get_search_analytics`
- `doctor`
- `tracker`
- `digest`

MCP defines tools/resources/prompts plus control and security considerations; its current specification emphasizes user consent and control, and tool invocation should retain a human-deniable boundary for sensitive actions. [MCP specification](https://modelcontextprotocol.io/specification/2025-11-25/)

### 15.2 REST API mode

Add `jobot serve` only after the local control plane is stable. Start with loopback/local use. Require API authentication and scope controls before remote access.

### 15.3 TUI

A Textual TUI may provide a useful power-user view of:

- scrape progress;
- application queue;
- saga state;
- budget/cost;
- approvals;
- failures.

It should consume existing APIs and not duplicate domain logic.

### 15.4 HTML reports

Continue lightweight HTML reports for offline sharing, funnel analysis, and export. Avoid heavy chart libraries unless measurements show they materially improve the experience.

### 15.5 Browser extension

Treat as a separate deployable product after v1.0:

- bookmark/clip jobs;
- show JoBot match data;
- assist autofill where permitted;
- connect to local `jobot serve` through an explicit trusted channel.

The extension must never become a bypass channel around site protections.

## 16. Phase 12 - Full Repository Refactor

**Priority:** P0/P1, continuous  
**Principle:** incremental restructure, behavior preservation, no massive rewrite.

The target organization should converge toward domain-first boundaries while reusing the existing modules and minimizing import churn:

```text
src/jobot/
  core/
    state/
    events/
    tasks/
    workflows/
    errors/
    contracts/
  control/
    goals/
    approvals/
    budgets/
    policies/
    trust/
    incidents/
  execution/
    workers/
    leases/
    checkpoints/
    effects/
    sandbox/
    browser/
    tools/
  ai/
    router/
    providers/
    prompts/
    profiles/
    evaluation/
  memory/
    semantic/
    episodic/
    procedural/
    retrieval/
    provenance/
  career/
    discovery/
    matching/
    companies/
    market/
    networking/
    interview/
    outcomes/
  applications/
    state_machine/
    preparation/
    submission/
    verification/
  documents/
    resume/
    cover_letter/
    pdf/
    ats/
  adapters/
    boards/
    ats/
    browser/
    email/
  observability/
    logs/
    tracing/
    metrics/
    events/
  plugins/
```

### 16.1 Refactor work packages

**RF-1: CLI monolith**  
Split `cli/main.py` into command groups while preserving every public command and exit behavior. Shared resolution helpers move into dedicated services.

**RF-2: Provider boundary**  
Split provider implementations from routing, accounting, prompt metadata, and health state. Implement a stable provider interface.

**RF-3: Adapter boundary**  
Introduce canonical domain DTOs and adapter-specific parsing modules. No adapter should reach directly into persistence internals.

**RF-4: Storage repositories**  
Separate domain services from SQLite implementation. Domain code depends on repository interfaces, while SQLite repositories perform persistence, indexing, and migrations.

**RF-5: Application protocol**  
Extract the state machine from the saga/orchestrator so state transitions are explicit and independently testable.

**RF-6: Event bus**  
Add typed events and subscribers for telemetry, alerts, GUI push, analytics, and audit storage.

**RF-7: Sidecar supervision**  
Encapsulate process lifecycle, EOF, backpressure, process-tree termination, locking, restart, and protocol errors.

**RF-8: Browser infrastructure**  
Separate session management, named actions, selectors, evidence, recovery, and site health from adapter definitions.

**RF-9: Memory abstraction**  
Make the currently documented memory tiers real and explicit. Do not add a large vector database unless scale measurements justify it.

**RF-10: Async hot paths**  
Convert network-heavy and browser orchestration paths to async internally with compatibility shims at the CLI boundary.

**RF-11: Plugin ABI**  
Formalize plugin contracts and permissions, but do not turn every internal module into a plugin.

**RF-12: Multi-worker foundations**  
Add worktree/ownership conventions and file/state synchronization as an extension of the core task graph, not a second control plane.

### 16.2 Refactor rules

After each work package:

1. run unit and integration tests;
2. run static analysis;
3. compare public interface inventory;
4. compare performance baseline;
5. inspect task/effect/event behavior;
6. update docs/contracts;
7. commit one coherent change;
8. update `worklog.md` and momentum queues.

No multi-week “all at once” branch.

## 17. Performance, Efficiency, and Resource-Consumption Program

**Priority:** P0 foundation, then continuous optimization  
**Goal:** maximize useful autonomous work per CPU, MB of RAM, network request, token, and second.

### 17.1 Optimization doctrine

- Measure before optimizing.
- Optimize the full loop, not one benchmark in isolation.
- Keep behavior identical while optimizing hot paths.
- Prefer deterministic code to LLM calls when the task is deterministic.
- Prefer caching and reuse over repeated computation.
- Prefer local processing when it reduces network cost and privacy exposure.
- Do not add infrastructure merely to make architecture look sophisticated.

### 17.2 CPU efficiency

- lazy-load expensive integrations;
- avoid import-time browser/LLM initialization;
- use bounded concurrency;
- batch parsing and normalization;
- batch embedding calls;
- avoid repeated regex recompilation;
- reuse compiled templates and document parsers;
- perform deterministic filters before semantic/LLM analysis;
- prefer connection/session reuse;
- eliminate polling loops with unnecessary sub-second wakeups.

### 17.3 Memory efficiency

- keep task contexts bounded;
- write long outputs to artifact files rather than model prompts;
- compact old transcripts into durable summaries;
- keep only active browser pages/contexts resident;
- deduplicate document artifacts by hash;
- compress large evidence artifacts where appropriate;
- keep vector indexes proportional to actual corpus size;
- expire caches with TTL and size limits;
- explicitly close HTTP sessions, browser pages, file handles, subprocesses, and DB cursors;
- use `tracemalloc` and RSS monitoring in soak tests.

### 17.4 Database efficiency

- batch writes inside explicit transactions;
- add indexes for task claiming, application lookup, event timeline, profile, job dedupe, and effect idempotency;
- use SQLite WAL and tuned `busy_timeout`;
- checkpoint WAL on a policy-driven schedule;
- keep large binary artifacts outside relational tables when they exceed configured thresholds, storing content hashes and paths instead;
- use SQLite online backup APIs for consistent snapshots;
- archive old telemetry and transient artifacts;
- avoid N+1 queries in GUI dashboards;
- measure migration duration on representative databases.

### 17.5 Network efficiency

- reuse HTTP connections;
- cache stable public job pages and metadata;
- use conditional requests with ETag/Last-Modified when available;
- deduplicate simultaneous requests;
- enforce per-domain concurrency and rate limits;
- use jittered backoff;
- stop polling when site health is degraded;
- avoid fetching deep company/recruiter information until a job is shortlisted.

### 17.6 Browser efficiency

- reuse persistent browser contexts safely;
- avoid launching a browser for API-capable ATSs;
- recycle pages when safe;
- capture full screenshots only at evidence checkpoints;
- compress evidence images;
- avoid arbitrary page reload loops;
- detect site health quickly and trip circuit breakers.

### 17.7 LLM/token efficiency

- deterministic preprocessing first;
- smaller context windows per task;
- stable prompt prefixes;
- retrieve only relevant skills/rules/memory;
- structured outputs rather than verbose free-form text;
- prompt and artifact deduplication;
- model routing by task complexity;
- cached embeddings and repeated-query results;
- retry with reduced context where safe;
- use local models for privacy-sensitive or low-cost tasks when quality clears eval thresholds.

### 17.8 GUI efficiency

- avoid re-rendering entire dashboards when one event changes;
- use event-driven updates;
- paginate large evidence and application sets;
- lazy-load screenshots/PDFs;
- keep charting lightweight;
- profile memory use of long-running GUI sessions.

### 17.9 Performance SLOs

First establish baseline, then commit targets. Suggested release targets:

- zero unbounded memory growth in a 1000-iteration soak;
- no duplicate external effects under retries;
- p95 sidecar RPC latency within an agreed local target;
- at least 1.2x throughput improvement for the async hot-path work package where behavior remains equivalent;
- materially reduced duplicate LLM calls and browser launches;
- bounded SQLite/WAL growth under scheduled workloads;
- install-to-first-success workflow within an average-user acceptable window.

Avoid arbitrary absolute RAM limits until measurements distinguish Python-only, GUI, browser, and LLM/provider processes.

## 18. Testing and Verification Pyramid

The testing system becomes a product capability rather than a last-step checklist.

### Level 1 - unit

- state transitions;
- serializers/schemas;
- URL parsing;
- candidate fact validation;
- prompt rendering;
- policy decisions;
- database repositories;
- selector resolver;
- cost accounting;
- PII redaction;
- answer bank;
- artifact hashing.

### Level 2 - contract tests

Every adapter must pass the same canonical contract suite:

- discover;
- normalize;
- inspect application questions;
- prepare;
- submit or dry-run;
- verify;
- report health.

### Level 3 - integration

Use mock ATS servers and deterministic fake browser/HTTP fixtures.

### Level 4 - end-to-end

Run the complete flagship journey using mock services and the actual sidecar/GUI.

### Level 5 - failure injection

Inject:

- network disconnect;
- DNS failure;
- 429;
- 500;
- malformed JSON;
- browser crash;
- tab closure;
- sidecar process death;
- provider timeout;
- corrupted checkpoint;
- DB lock;
- duplicate event;
- duplicate effect;
- stale selector;
- invalid candidate data;
- prompt injection;
- plugin permission violation.

### Level 6 - soak and leak

Run long-lived loops with RSS, CPU, SQLite WAL, file descriptor, browser-process, and artifact-growth monitoring.

### Level 7 - security

- CodeQL;
- dependency audit;
- secret scanning;
- URL/parser fuzzing;
- prompt injection corpus;
- Tauri capability regression;
- vault permission tests;
- plugin sandbox tests;
- credential-redaction tests.

### Level 8 - release candidate

Fresh installations on all Tier-1 platforms; upgrade from previous release; backup/restore; rollback; CLI; GUI; package install; Docker; desktop startup; doctor.

## 19. Documentation Generation Program

**Priority:** P0  
**Goal:** the project must be understandable, installable, operable, maintainable, and supportable without private context.

### 19.1 Canonical docs set

Create and maintain:

```text
docs/
  README.md
  architecture.md
  architecture/
    control-plane.md
    execution.md
    state-machines.md
    browser.md
    memory.md
    model-routing.md
    eventing.md
  getting-started/
    installation.md
    quickstart.md
    first-application.md
    doctor.md
    troubleshooting.md
  user/
    profiles.md
    discovery.md
    matching.md
    applications.md
    approvals.md
    resume.md
    interview.md
    tracker.md
    networking.md
    market-intelligence.md
    backups.md
    privacy.md
  reference/
    cli.md
    rpc.md
    configuration.md
    schemas.md
    events.md
    state-machines.md
    adapter-capabilities.md
    error-codes.md
  security/
    threat-model.md
    secure-configuration.md
    plugin-security.md
    prompt-injection.md
    secret-management.md
    vulnerability-disclosure.md
  adapters/
    overview.md
    support-matrix.md
    adapter-development.md
    browser-site-health.md
  ai/
    providers.md
    routing.md
    prompts.md
    evals.md
    local-models.md
  operations/
    runbook.md
    incident-response.md
    backup-restore.md
    database-migrations.md
    telemetry.md
    release-process.md
    rollback.md
    performance.md
  developer/
    contributing.md
    testing.md
    architecture-decisions.md
    plugin-development.md
    browser-fixtures.md
  planning/
    MASTER_PLAN.md
    decisions.md
    milestones.md
    archive/
```

### 19.2 Root project artifacts

Keep a small, truthful root surface:

- `AGENTS.md`;
- `README.md`;
- `CHANGELOG.md`;
- `LICENSE`;
- `SECURITY.md`;
- `CONTRIBUTING.md`;
- `CODE_OF_CONDUCT.md`;
- `MASTER_PLAN.md`;
- `SETUP.md` only if its scope remains useful; otherwise make it a short pointer to docs;
- `worklog.md`;
- `queues/now.md`, `next.md`, `blocked.md`, `improve.md`, `recurring.md`.

### 19.3 Documentation generation automation

Generate where possible:

- CLI reference from Typer command metadata;
- RPC reference from the sidecar schema registry;
- adapter support matrix from adapter metadata;
- configuration reference from Pydantic/config schemas;
- event catalog from event definitions;
- version compatibility tables from CI matrix;
- changelog entries from merged PR labels where appropriate;
- benchmark summaries from CI artifacts.

### 19.4 Docs quality gates

- links valid;
- code samples runnable;
- version numbers current;
- no stale feature claims;
- privacy docs exactly match telemetry code;
- release notes distinguish hermetic vs live validation;
- screenshots are generated from supported builds;
- all safety caveats are visible where a user performs a risky operation.

### 19.5 Docs website

Use a lightweight docs site such as VitePress only if the current build stack can support it without significant maintenance cost. It should be generated from the same repository files, not become a second source of truth.

## 20. Project Directory Cleanup Program

**Priority:** P0/P1  
**Goal:** eliminate stale, duplicate, generated, misleading, and unnecessary repository content while preserving useful history.

### 20.1 Cleanup policy

Never delete based on filename alone. For every candidate:

1. search references;
2. inspect build/runtime usage;
3. classify as keep / move / archive / regenerate / delete;
4. create a cleanup manifest;
5. run full tests after the change.

### 20.2 Immediate cleanup candidates to verify

- duplicate root planning documents superseded by `MASTER_PLAN.md`;
- duplicated Plan1 PDF/markdown artifacts;
- stale `JoBot_Refactor_Plan.md` once its content is represented or archived;
- old Merge Plan PDF once the new master plan becomes authoritative;
- `cover.html` if unused by the current build or docs pipeline;
- generated `dist/`, `build/`, `coverage/`, cache directories, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, frontend install trees, local browser profiles, and temporary logs if ever committed;
- obsolete historical docs that are not referenced and have no archival value;
- stale task queues that contradict repository state.

### 20.3 Planning archive

Move supplied plans to an explicit archive such as:

```text
docs/planning/archive/2026-08-15/
  Plan1.md
  Plan1.pdf
  Plan2.md
  Plan3.md
  plan4.md
  plan5.md
  manifest.md
```

The archive is retained for traceability, but `MASTER_PLAN.md` becomes the current authority.

### 20.4 Historical documentation

Retain useful historical decisions under `docs/history/`, but mark them clearly as historical. Do not let old architectural descriptions appear in current README or onboarding flows.

### 20.5 Ignore and clean patterns

Ensure `.gitignore` includes all appropriate caches, virtual environments, credentials, coverage fragments, browser artifacts, private key containers, local DB backups, and generated build outputs.

### 20.6 Final cleanup gate

The repository root should contain only intentional human-facing/project-control files. A new contributor should be able to understand which file is authoritative within minutes.

## 21. Database, Migration, Backup, and Data Lifecycle

**Priority:** P0

### 21.1 Versioned migrations

Introduce:

```text
schema_migrations
  version
  applied_at
  checksum
```

Example sequence:

```text
001_initial
002_events
003_task_leases
004_approvals
005_budgets
006_effects
007_memory_provenance
008_answer_bank
009_company_entities
010_outcome_learning
```

### 21.2 CLI

Provide:

```text
jobot db status
jobot db migrate
jobot db backup
jobot db restore
jobot db verify
```

### 21.3 Backups

`jobot backup` must include exactly what is needed to restore user work:

- SQLite state;
- encrypted profiles;
- required application metadata;
- memory;
- artifact manifests and optionally artifacts;
- safe configuration metadata.

Exclude ephemeral browser caches and unnecessary secrets.

### 21.4 Restore drills

Restore a backup into a clean environment, run integrity checks, open the GUI/CLI, inspect applications, and resume a paused workflow.

### 21.5 Data retention

Define retention categories for:

- raw job descriptions;
- screenshots;
- PDFs;
- logs;
- traces;
- telemetry;
- recruiter emails;
- historical applications;
- memories;
- cached web content.

Provide `jobot purge` with scoped deletion and confirm irreversible destruction.

## 22. Privacy and Data Governance

**Priority:** P0

JoBot's privacy story should become a documented product capability, not a README adjective.

### 22.1 Data classification

Classify data into:

- public external data;
- user-provided profile data;
- credentials/secrets;
- application content;
- sensitive personal data;
- operational telemetry;
- research/cache data.

### 22.2 Provider routing policy

Allow users to specify which providers may receive which classes of data. Sensitive data may require local-only models or explicit approval.

### 22.3 PII protection

The PII masker remains a defense layer, not the sole security boundary. Redact at:

- LLM calls;
- logs;
- traces;
- crash reports;
- analytics;
- screenshots where technically feasible;
- debug exports.

### 22.4 Telemetry

If telemetry exists in v1:

- opt-in only;
- off by default if the privacy promise requires it;
- no application contents;
- no raw job URLs where avoidable;
- no credentials;
- versioned schema;
- documented retention;
- immediate kill switch;
- test that code and docs match.

### 22.5 Data portability

CSV and JSON export/import must be round-trip safe, validated, deduplicated, and versioned.

### 22.6 User deletion

Users must be able to purge application history, evidence, logs, and profile data by category.

## 23. Plugin and Extension Security

**Priority:** P0 security design, P2 ecosystem

Plugin lifecycle:

```text
manifest
 -> source/hash verification
 -> dependency audit
 -> capability declaration
 -> permission evaluation
 -> sandbox selection
 -> install
 -> health check
 -> runtime policy enforcement
```

Permissions may include:

```yaml
filesystem:
  - candidate-profile
network:
  - api.example.com
browser:
  - site-name
secrets:
  - none
```

Default is deny-by-default.

Unknown plugins must not gain unrestricted access to candidate credentials, host files, or browser profiles.

Later plugin gallery work must separate:

- discovery and metadata;
- package verification;
- capability review;
- install;
- runtime enforcement.

Community plugins are never allowed to weaken core security invariants.

## 24. Release Engineering and v1.0.0 Launch Program

**Priority:** P0

### 24.1 Version authority

Use `pyproject.toml` as the authoritative product version and synchronize:

```text
pyproject.toml
   -> root package metadata
   -> GUI package metadata
   -> Tauri config
   -> CLI --version
   -> Git tag
   -> Docker tag
   -> release metadata
```

The synchronizer must be idempotent and CI must fail if versions drift.

### 24.2 Supported channels

v1.0 should produce:

1. PyPI wheel/sdist;
2. GHCR container image;
3. signed/notarized desktop artifacts to the extent credentials and budget allow;
4. source archive and SBOM/provenance.

### 24.3 CI layers

```text
PR
 -> lint
 -> format
 -> type check
 -> unit tests
 -> coverage
 -> contract tests
 -> security checks
 -> integration tests
 -> build

main/nightly
 -> full integration
 -> browser mocks
 -> failure injection
 -> soak subsets
 -> eval suite

release candidate
 -> all of the above
 -> package install
 -> Docker smoke
 -> desktop build
 -> upgrade test
 -> backup/restore
 -> attestation verification

stable release
 -> artifact verification
 -> publication
 -> smoke test
 -> release notes
```

### 24.4 Test matrix

Tier 1 platforms should explicitly include the platforms supported by the desktop artifact and the strongest user base target. Suggested:

- macOS;
- Windows;
- Linux.

Treat WSL2 and headless Docker as explicitly documented support tiers rather than silently assuming full GUI parity.

Python CI should cover 3.11-3.13 when supported by dependencies.

### 24.5 Distribution hardening

- PyPI Trusted Publishing;
- GHCR multi-architecture images where feasible;
- desktop CI builds for Windows/macOS/Linux;
- real icons;
- update channel;
- updater signature verification;
- code signing where credentials are available;
- notarization decision documented honestly;
- restrictive Tauri CSP;
- artifacts signed/attested;
- clean-install smoke tests.

### 24.6 Release gates

**Functional:** critical unit/integration/eval suites pass.  
**Reliability:** crash recovery, duplicate submission, approval/resume, browser reconnect, provider fallback all pass.  
**Security:** CodeQL, dependency audits, secret scan, Tauri permissions, plugin tests, prompt injection suite pass.  
**Packaging:** wheel, sdist, Docker, GUI, `jobot doctor`, migrations, upgrade path pass.  
**Documentation:** release docs match exact behavior.  
**Supportability:** backups and incident runbooks exercised.

### 24.7 Rollback

Every release needs a written rollback path:

- revoke broken release artifacts if necessary;
- publish patched release;
- maintain DB downgrade or forward-fix policy;
- identify safe artifact versions;
- document how to recover corrupted user state;
- disable unsafe adapters/features via remote-free local feature configuration when possible.

## 25. `jobot doctor` as the Release-Critical User Experience

`jobot doctor` becomes the single diagnostic authority for user support.

Checks:

```text
Runtime
  Python version
  OS
  architecture
  SQLite
  filesystem
  permissions

Security
  keyring
  vault
  permissions
  unsafe config

Browser
  Patchright
  Chromium
  browser profiles
  required binaries

Documents
  PDF extraction
  PDF compilation backend(s)
  template health

AI
  provider configuration
  provider health
  routing config
  local model availability

Adapters
  registry integrity
  capability matrix
  site health

Control plane
  migrations
  event ledger
  task queue
  worker
  scheduler
  event bus

Release
  package version
  GUI version
  database compatibility
  supported-platform flags
```

Support:

```text
jobot doctor
jobot doctor --json
jobot doctor --fix-safe
```

`--fix-safe` may perform only non-destructive remediation such as cache cleanup or configuration normalization. It must never change credentials or external application state without explicit confirmation.

## 26. Average-User Onboarding and First-Run Experience

Several supplied plans focused heavily on infrastructure and competitor features but under-specified the first ten minutes of use. This is a release blocker for an average user.

### 26.1 First-run sequence

```text
Install
 -> jobot doctor
 -> privacy / telemetry choice
 -> choose or create profile
 -> import resume
 -> confirm candidate facts
 -> configure LLM provider or local model
 -> choose job filters
 -> test discovery
 -> preview one application
 -> run first controlled application
```

### 26.2 No hidden configuration

Every required external dependency must be identified by `doctor`, including optional providers and PDF tooling.

### 26.3 Safe defaults

Default to:

- human approval before submission;
- low volume;
- conservative rate limits;
- no external recruiter messaging;
- no telemetry unless explicitly enabled;
- no untrusted plugin execution;
- no arbitrary remote API exposure;
- backup prompt after profile creation.

### 26.4 Progressive trust

The UI can offer more automation after measured success:

```text
supervised
 -> guided
 -> bounded autonomous
 -> trusted bounded workflow
```

Trust must be reversible.

## 27. Operations, Incident Response, and Post-Launch Maintenance

### 27.1 Incidents

Every incident records:

- severity;
- impact;
- affected users/applications;
- timeline;
- last known good version;
- root cause;
- mitigation;
- corrective action;
- eval/test added to prevent recurrence.

### 27.2 Recurring maintenance

- weekly issue/incident triage;
- weekly security alert review;
- monthly release train;
- adapter-health monitoring;
- dependency update review;
- browser compatibility checks;
- model/provider price and capability review;
- external-intelligence digest;
- quarterly architecture review.

### 27.3 External intelligence loop

Track architecture-bearing updates from:

- durable workflow engines;
- agent orchestration systems;
- memory/retrieval systems;
- browser/desktop automation systems;
- eval/observability projects;
- model gateways;
- MCP and other open protocols;
- security advisories;
- relevant job-search platforms.

Use open-source sources first. Adopt only what local evals support.

### 27.4 Release channels

```text
nightly -> alpha -> beta -> rc -> stable
```

Each channel has explicit support expectations.

## 28. Competitive and Open-Source Feature Preservation Matrix

This matrix is the safeguard against losing ideas while unifying the plans.

| Capability / idea | Source plans | Master priority | Integrated location |
|---|---|---:|---|
| Durable task queue | Plan1, AGENTS.md | P0 | Phase 2 |
| Atomic leases | Plan1 | P0 | Phase 2 |
| Attempts / heartbeats | Plan1 | P0 | Phase 2 |
| Event ledger | Plan1 | P0 | Phase 2 |
| Durable waits / approvals | Plan1, Plan2 | P0 | Phases 2-3 |
| Effect ledger | Plan1 | P0 | Phase 3 |
| Idempotency | Plan1 | P0 | Phase 3 |
| Unknown states | Plan1 | P0 | Phase 3 |
| Reconciliation | Plan1 | P0 | Phase 3 |
| Application saga | Plan1, Plan2 | P0 | Phase 3 |
| Browser session manager | Plan1 | P0 | Phase 4 |
| Selector registry/healing | Plan3 | P0 | Phase 4 |
| Browser evidence | Plan1 | P0 | Phase 4 |
| CAPTCHA/human boundary | Plan1, Plan2 | P0 | Phase 4 |
| Site-health circuit breaker | Plan1 | P0 | Phase 4 |
| CXS adapter family | Plan3 | P0/P1 | Phase 4 |
| Adapter boundary schemas | Plan3 | P0 | Phase 4 |
| Proxy plumbing | Plan3 | P2 / policy-bound | Phase 4 |
| LLM streaming | Plan2 | P1 | Phase 5 |
| ModelRouter v2 | Plan1 | P0 | Phase 5 |
| Prompt versioning | Plan1 | P0 | Phase 5 |
| Candidate truth | Plan1 | P0 | Phase 5 |
| Grounded question answering | Plan1, Plan2 | P0 | Phase 5 |
| Resume PDF ingestion | Plan2 | P1 | Phase 5 |
| Resume tailoring reviewer | Plan1, Plan2 | P0 | Phase 5 |
| ATS text + visual verification | Plan1 | P0 | Phase 5 |
| Job matching pipeline | Plan1, Plan2 | P0/P1 | Phases 5-6 |
| Job fraud detection | Plan1, Plan2 | P1 | Phase 10 |
| Multi-profile | Plan2 | P1 | Phase 6 |
| JobSpy | Plan1, Plan2, plan3 | P1 | Phase 10 |
| Kanban tracker | Plan2, Plan3 | P0/P1 | Phase 7 |
| Funnel analytics | Plan3 | P0/P1 | Phase 7 |
| Screening answer bank | Plan3 | P0/P1 | Phase 10 |
| Apply-method classification | Plan3 | P0/P1 | Phase 10 |
| Data export/import | Plan3 | P0/P1 | Phase 10 |
| Job clipping | Plan3 | P1 | Phase 10 |
| Follow-up automation | Plan2, Plan3 | P1 | Phase 10 |
| Email status watcher | Plan2, Plan3 | P1 | Phase 10 |
| Interview preparation | Plan1, Plan2 | P1 | Phase 10 |
| Networking | Plan1, Plan2, Plan3 | P1/P2 | Phase 10 |
| Salary intelligence | Plan1, Plan2 | P1 | Phase 10 |
| Resume A/B testing | Plan2, Plan3 | P1/P2 | Phase 10 |
| LinkedIn profile scoring | Plan2 | P2 | Phase 10 |
| Multi-language resumes | Plan2 | P2 | Phase 10 |
| Proactive discovery | Plan1, Plan2, Plan3 | P1/P2 | Phase 10 |
| Career graph | Plan1 | P2 | Phase 10 |
| Outcome learning | Plan1, Plan2 | P0/P1 | Phase 8 |
| Career intelligence | Plan1 | P2 | Phase 10 |
| OpenTelemetry | Plan1, Plan2, Plan3 | P0 | Phase 8 |
| Audit log | Plan2 | P0 | Phases 2/8 |
| Structured JSON logs | Plan2, Plan4 | P0 | Phase 8 |
| Trust scoring | Plan1, Plan2 | P1/P2 | Phase 8 |
| Budgets/cost dashboard | Plan1, Plan2 | P0/P1 | Phases 2/7 |
| Evals | Plan1, AGENTS.md | P0 | Phase 8 |
| Failure injection | Plan1, Plan4 | P0 | Phase 18 |
| Soak testing | Plan4 | P0 | Phase 18 |
| Sandbox | Plan1, Plan3 | P1/P2 | Phases 5/11 |
| Plugin permissions | Plan1, Plan3, Plan5 | P0 security | Phase 23 |
| Plugin gallery | Plan3 | P2 | Phase 23 |
| MCP | Plan1, Plan3 | P1 | Phase 15 |
| REST/API server | Plan2 | P1/P2 | Phase 15 |
| TUI | Plan2 | P1/P2 | Phase 15 |
| HTML dashboard | Plan2 | P1 | Phase 15 |
| Browser extension | Plan2, Plan3 | P2 | Phase 15 |
| Direct ATS APIs | Plan2 | P1 | Phase 10 |
| Database migrations | Plan1, Plan4 | P0 | Phase 21 |
| Backup/restore | Plan1, Plan4 | P0 | Phase 21 |
| `jobot doctor` | Plan1, Plan4 | P0 | Phase 25 |
| PyPI / Docker / desktop artifacts | Plan4 | P0 | Phase 24 |
| Trusted PyPI publishing | Plan4, Plan5 | P0 | Phase 24 |
| SBOM/provenance | Plan1, Plan4, Plan5 | P0 | Phase 24 |
| Governance docs | Plan2, Plan4, Plan5 | P0 | Phase 19 |
| Repo cleanup | Plan5 + user request | P0 | Phase 20 |
| Full refactor | Plan1, Plan2, Plan3 + user request | P0/P1 | Phase 16 |
| Performance/resource optimization | AGENTS.md + user request | P0 | Phase 17 |
| Self-improvement | Plan1, AGENTS.md | P2 | Phase 9 |
| Skill extraction | Plan1, AGENTS.md | P2 | Phase 9 |
| Multi-machine workers | Plan1, Plan3 | P2 | Phase 11/10 |

## 29. Release-Critical End-to-End Scenario

The most important test in the entire repository is the durable verified application scenario.

```text
1. Resolve job URL
2. Persist canonical job
3. Deduplicate and validate freshness
4. Create goal/task
5. Evaluate risk policy
6. Evaluate candidate fit
7. Gather candidate facts with provenance
8. Plan resume tailoring
9. Generate tailored resume
10. Review independently
11. Generate cover letter if required
12. Verify documents (text + ATS + visual)
13. Generate/validate screening answers
14. Create approval request
15. Persist waitpoint
16. User approves/edits/defers
17. Resume after approval
18. Claim submission task with lease
19. Prepare browser/API session
20. Record ExternalEffect and idempotency key
21. Fill application
22. Validate final form state
23. Submit
24. Observe external result
25. Verify confirmation or enter SUBMISSION_UNKNOWN
26. Capture evidence
27. Persist state and event
28. Update tracker/outcome
29. Update memory with provenance
30. Emit metrics/trace
31. Generate improvement candidate
32. Schedule next action if appropriate
```

Failure-inject after steps 4, 8, 12, 15, 18, 22, 24, and 27. Repeat each scenario multiple times.

**Release rule:** if any injected failure produces a duplicate external effect, silent data loss, incorrect `SUBMITTED` status, or untraceable transition, v1.0 is blocked.

## 30. Project Completion Definition

JoBot is ready for an average-user v1.0 only when all of the following are true.

### Reliability

- durable task state exists;
- worker leases and recovery work;
- long waits survive restarts;
- application state and task state are explicit;
- external effects are idempotent and reconciled;
- unknown states are first-class;
- browser sessions recover safely;
- no silent retry storms;
- incidents are visible.

### AI quality

- no unsupported candidate claims in critical outputs;
- prompts and models are versioned;
- model routing is budgeted;
- verification is independent;
- critical evals are release-gated.

### Product

- average user onboarding works;
- CLI is modular and documented;
- GUI control plane works;
- approval and evidence UX works;
- application tracking works;
- backups/restore work;
- export/import works.

### Security

- release-blocking advisories fixed or explicitly accepted with rationale;
- CodeQL/dependency/secret scans clean to the agreed threshold;
- Tauri permissions least-privilege;
- vault protected;
- plugin permissions enforced;
- prompt-injection boundary tested;
- no secret leakage into logs/evidence/telemetry.

### Performance

- benchmark baseline and regression budgets exist;
- no unbounded memory leak in soak tests;
- browser/session reuse works;
- redundant LLM calls are controlled;
- task and DB queries are indexed and bounded.

### Release

- one version authority;
- PyPI trusted publishing;
- signed/attested artifacts;
- Docker image published and smoke-tested;
- desktop installers built on supported OSes;
- update behavior verified;
- `jobot doctor` passes;
- migrations and upgrades tested;
- release notes honest about live adapter validation;
- docs site and governance docs live.

### Support

- incident runbook;
- security disclosure path;
- rollback procedure;
- issue templates;
- community/contribution instructions;
- recurring maintenance schedule.

## 31. Execution Workflow for Every Implementation Task

The same protocol is applied to code, documentation, infrastructure, and adapters.

```text
1. Read the relevant contract and code
2. Write/update task specification
3. Identify risks and dependencies
4. Implement the smallest coherent change
5. Add/update verification immediately
6. Run targeted tests
7. Run the appropriate full gates
8. Review logs/artifacts/evidence
9. Update worklog and momentum queues
10. Record a decision when direction changed
11. Record a failure if the attempt exposed a new boundary
12. Turn recurring failures into evals/guardrails
13. Merge only when the release gate remains green
```

Parallel work is allowed only when tasks have explicit ownership boundaries, separate worktrees where needed, and no shared mutable working-tree edits.

## 32. Decision Register and Default Assumptions

The plans contain many unresolved questions. To prevent the entire program from stalling, the Master Plan uses safe defaults while retaining decision gates.

| Decision | Default for this plan | Revisit when |
|---|---|---|
| v1 target | Local-first single-user product | After v1 adoption evidence |
| SaaS | Out of v1 scope | After local product proves demand |
| Final submission | Human approval by default, bounded trust later | After verified real-world outcome data |
| GUI | v1 required for average-user release | If schedule becomes materially unsafe; then CLI-first release must be explicit |
| Browser extension | P2 | After core GUI/serve interface is stable |
| MCP | P1 optional interface | After control plane contracts are stable |
| API server | P1/P2 | After local security model is complete |
| Database | SQLite WAL for v1 | Migrate to Postgres only when measured concurrency/scale requires it |
| Browser backend | Patchright behind capability interface; support replacement path | If maintenance or compatibility risk becomes unacceptable |
| LLM provider | Provider-neutral, local-first, no shared API keys | Based on eval/cost results |
| Resume engine | Keep LaTeX path plus robust fallback | After benchmark of HTML/PDF alternatives |
| Telemetry | Opt-in, minimized, kill-switch | User/community feedback |
| Remote multi-worker | P2 | After single-machine durability is proven |
| Bulk apply | P2/experimental, strict caps and compliance rules | Only with evidence of safe value |
| LinkedIn automation | Explicitly policy-gated and optional | Based on platform terms and user authorization |
| Code signing | Do it where practical; document any deferred platform credential | Before stable user-facing installers |
| Mac notarization | Decision gate; defer only with explicit caveat | Before broad nontechnical adoption |
| Windows signing | Prefer trusted signing path; otherwise document SmartScreen friction | Before stable release |
| Docs site | VitePress or similarly lightweight static docs | After docs structure settles |
| Structured logging dependency | Prefer stdlib structured formatter unless a dedicated library materially improves maintainability | Benchmark after instrumentation |

## 33. Unified Timeline

The exact duration depends on staffing and live validation access; sequence and gates matter more than calendar promises.

| Stage | Main objective | Priority | Release impact |
|---|---|---:|---|
| Wave 0 | Truth/baseline/freeze | P0 | Release blocker |
| Wave 1 | Security/supply chain/hygiene | P0 | Release blocker |
| Wave 2 | Durable execution | P0 | Release blocker |
| Wave 3 | Application correctness/effects | P0 | Release blocker |
| Wave 4 | Browser/adapters | P0 | Release blocker |
| Wave 5 | Candidate truth/AI/doc pipeline | P0 | Release blocker |
| Wave 6 | GUI/control plane/onboarding | P0 | Release blocker |
| Wave 7 | Observability/evals | P0 | Release blocker |
| Wave 8 | Packaging/release artifacts | P0 | Release blocker |
| Wave 9 | P1 capability expansion | P1 | Post-core or same release if gates stay green |
| Wave 10 | Self-improvement/strategic moat | P2 | Post-1.0 |
| Wave 11 | Multi-machine/general agent OS | P2/P3 | Post-1.0 |

The product should not advance to volume-oriented automation simply because a capability is technically available. Every promotion requires evidence that the previous layer is reliable.

## 34. Final Master Backlog

### P0 - must be complete before stable v1.0

- [ ] Baseline inventory and scorecard
- [ ] Canonical version authority
- [ ] Security vulnerability remediation and accepted-risk register
- [ ] URL/site classification hardening
- [ ] Tauri CSP and least-privilege capabilities
- [ ] Vault hardening
- [ ] SHA-pinned CI and minimum permissions
- [ ] pip/npm/cargo/gitleaks/actionlint security gates
- [ ] CodeQL for Python/JavaScript/Rust where applicable
- [ ] SBOM + artifact provenance
- [ ] PyPI Trusted Publishing
- [ ] Persistent task queue
- [ ] Atomic task leases
- [ ] Task attempts and heartbeats
- [ ] Event ledger
- [ ] Checkpoints and durable waits
- [ ] Quarantine/dead-letter
- [ ] Cancellation
- [ ] Application state machine
- [ ] External effect ledger
- [ ] Idempotency keys
- [ ] Unknown states
- [ ] Reconciliation
- [ ] Durable approvals
- [ ] Candidate fact provenance
- [ ] Grounded question answering
- [ ] Resume + cover document verification
- [ ] Browser session manager
- [ ] Selector registry/healing
- [ ] Browser evidence capture
- [ ] Site health/circuit breaker
- [ ] Adapter boundary schemas
- [ ] Independent verifier
- [ ] Failure injection
- [ ] Soak tests
- [ ] Structured logs
- [ ] Traces/metrics
- [ ] Critical eval suites
- [ ] GUI dashboard/control plane
- [ ] Approval inbox
- [ ] Evidence viewer
- [ ] Incident viewer
- [ ] Job tracker/funnel basics
- [ ] First-run onboarding
- [ ] `jobot doctor --json`
- [ ] DB migrations
- [ ] Backup/restore
- [ ] Upgrade tests
- [ ] Full docs set
- [ ] Cleanup and archive migration
- [ ] Refactor of CLI monolith and other high-risk hotspots
- [ ] Performance baseline and regression gates
- [ ] release candidate pipeline
- [ ] final user-facing release notes and support runbook

### P1 - high-value immediately after core stability

- [ ] LLM streaming
- [ ] Multi-profile support
- [ ] Resume PDF ingestion
- [ ] JobSpy/multi-board integration
- [ ] ATS family expansion
- [ ] Greenhouse/Lever/Ashby/SmartRecruiters direct integrations where authorized
- [ ] Embedding + structured matching
- [ ] Answer bank/autofill reuse
- [ ] Apply-method classification
- [ ] Follow-ups
- [ ] Email synchronization
- [ ] Data export/import
- [ ] Job clipping
- [ ] Resume variants / A-B measurement
- [ ] Interview upgrades
- [ ] Proactive scheduled discovery
- [ ] OpenTelemetry external export
- [ ] MCP
- [ ] API server
- [ ] TUI
- [ ] HTML analytics reports
- [ ] local model/Ollama pathway

### P2 - strategic moat

- [ ] Browser extension
- [ ] Networking graph
- [ ] LinkedIn profile scoring
- [ ] Multilingual resumes
- [ ] salary negotiation toolkit
- [ ] career opportunity graph
- [ ] skill extraction
- [ ] trajectory mining
- [ ] automated eval generation
- [ ] bounded self-improvement
- [ ] adaptive model routing based on outcome evidence
- [ ] plugin gallery
- [ ] remote sandbox
- [ ] multi-machine workers
- [ ] high-volume campaign mode under strict policy controls

## 35. Research and Reference Base

### User-supplied planning artifacts

- `agents.md` - governing doctrine
- `Plan1.md` - reliability-first architecture and durable application plan
- `Plan1.pdf` - PDF form of the Plan1 architectural plan
- `Plan2.md` - repo audit, competitive landscape, feature integration, and release sequence
- `Plan3.md` - updated refactor and GUI-first feature backlog
- `plan4.md` - production readiness and v1 release engineering
- `plan5.md` - vulnerability, CodeQL, dependency, and repository hardening

### JoBot repository artifacts inspected

- `README.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/publish.yml`
- `.github/dependabot.yml`
- `package.json`
- `gui/package.json`
- `gui/src-tauri/tauri.conf.json`
- `gui/src-tauri/capabilities/default.json`
- repository tree and current Git history metadata

### External research used in synthesis

- Vite 8 release and Node compatibility: https://vite.dev/blog/announcing-vite8
- Tauri security model and capabilities: https://v2.tauri.app/security/
- MCP specification: https://modelcontextprotocol.io/specification/2025-11-25/
- OpenTelemetry: https://opentelemetry.io/docs/
- Greenhouse Job Board API: https://developers.greenhouse.io/job-board/
- Lever Developer API: https://hire.lever.co/developer/documentation
- GitHub artifact attestations: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- PyPI Trusted Publishers: https://docs.pypi.org/trusted-publishers/
- OWASP LLM01:2025 Prompt Injection: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- LinkedIn User Agreement: https://www.linkedin.com/legal/user-agreement

### Architecture projects to monitor, not cargo-cult

- LangGraph
- Temporal
- Letta
- PydanticAI
- OpenHands
- AutoGen / Microsoft Agent Framework
- Semantic Kernel
- Google ADK
- DSPy
- Mastra
- AgentScope
- OpenClaw
- Hermes Agent
- Paperclip
- Superpowers
- gstack
- SWE-agent / mini-SWE-agent
- LiteLLM
- Graphiti
- Langfuse
- Opik
- Invariant
- vLLM
- E2B
- Daytona
- LlamaIndex
- Haystack
- Mem0
- agent-sandbox
- MCP ecosystem

The guiding rule from `AGENTS.md` applies: external ideas are hypotheses until a local eval, replay, shadow run, or production measurement demonstrates value.

## 36. Final Recommendation

JoBot should be built as **one durable operating system with one user-facing surface and many replaceable capability layers**.

The strongest architecture is:

```text
                    JoBot
                      |
             +--------+--------+
             |                 |
        General Agent      Career Harness
             |                 |
           Tools       +-------+-------+
             |         |       |       |
         Research   Search   Apply   Interview
             |         |       |       |
             +---------+-------+-------+
                       |
                 Durable Runtime
                       |
          +------------+------------+
          |            |            |
        State        Memory      Evidence
          |            |            |
          +------------+------------+
                       |
             Policy + Verification
                       |
                  Control Plane
                       |
             CLI / GUI / MCP / API
```

Do not optimize for the number of sites supported until the core loop is dependable. Do not optimize for model cleverness before task state and verification are reliable. Do not optimize for agent count before the single-agent baseline is strong. Do not claim self-improvement without eval evidence. Do not treat a browser click as proof of an external effect.

The end state is not a giant prompt and not a swarm of chatbots. It is a **durable, observable, policy-governed execution system** in which successful job-search behavior becomes repeatable, explainable, measurable, and eventually self-improving.

## Appendix A - Phase Exit Gate Checklist

### Gate G0 - Truth

- [ ] Baseline report generated
- [ ] current repository commit recorded
- [ ] all supplied plans archived and mapped
- [ ] stale claims identified

### Gate G1 - Security

- [ ] release-blocking vulnerabilities fixed/accepted
- [ ] URL classification hardened
- [ ] Tauri CSP and capabilities hardened
- [ ] vault hardened
- [ ] secrets scans clean
- [ ] CI Actions pinned

### Gate G2 - Durability

- [ ] task persistence
- [ ] atomic leasing
- [ ] heartbeats
- [ ] checkpoints
- [ ] durable waits
- [ ] quarantine
- [ ] recovery

### Gate G3 - Application correctness

- [ ] state machine
- [ ] effect ledger
- [ ] idempotency
- [ ] reconciliation
- [ ] unknown states
- [ ] approval
- [ ] evidence

### Gate G4 - Browser / adapters

- [ ] browser lifecycle
- [ ] selector registry
- [ ] selector fallback/healing
- [ ] site health
- [ ] evidence capture
- [ ] failure injection

### Gate G5 - AI

- [ ] candidate truth
- [ ] grounded QA
- [ ] document verification
- [ ] prompt versioning
- [ ] router cost accounting
- [ ] critical evals

### Gate G6 - UX

- [ ] onboarding
- [ ] dashboard
- [ ] tracker
- [ ] approval inbox
- [ ] evidence viewer
- [ ] incident view
- [ ] accessibility baseline

### Gate G7 - Release

- [ ] version synchronization
- [ ] migrations
- [ ] clean install
- [ ] upgrade
- [ ] backup/restore
- [ ] wheel/sdist
- [ ] Docker
- [ ] desktop
- [ ] SBOM
- [ ] attestation
- [ ] release notes
- [ ] docs

## Appendix B - Required Persistent Project Operating Files

The implementation workspace should maintain the following living state, consistent with `AGENTS.md`:

```text
AGENTS.md
MASTER_PLAN.md
worklog.md
queues/
  now.md
  next.md
  blocked.md
  improve.md
  recurring.md

docs/
  architecture/
  operations/
  security/
  user/
  reference/
  planning/

artifacts/
evals/
runs/
incidents/
```

Every substantial execution should leave:

- visible state;
- evidence;
- at least one reusable artifact;
- one explicit next action;
- one improvement candidate or confirmed “no improvement needed” record.

## Appendix C - One-Sentence Definition of Done

> **JoBot is done for v1.0 when an average user can install it, configure a profile, discover a suitable job, generate and verify grounded application materials, review and approve a submission, let JoBot execute the supported application workflow, survive an injected crash without duplicating the external effect, inspect the evidence and outcome, back up and restore the state, and receive a documented, signed/attested release artifact - all under explicit policy controls and measurable eval gates.**
