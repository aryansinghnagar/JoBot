# Security Policy

JoBot is a local-first, single-user desktop/CLI application. This document
covers supported versions, how to report vulnerabilities, known accepted
residual risks, and the secure-configuration and supply-chain expectations for
the project.

## Supported Versions

JoBot is on the `0.2.x` pre-release line. Security fixes land on `main`
first and are backported to the Active line. There are no backport
branches for older lines (anything before `0.2.x` is unsupported).

| Version | Status    | Notes                                                                 |
| ------- | --------- | --------------------------------------------------------------------- |
| `0.2.x` | Active    | Current development line. Fixes land on `main` and ship in the next `0.2.y` patch release. |
| `main` branch | Trunk-of-truth | All fixes are committed here first; tagged releases are cut from `main`. |
| `0.1.x` | Unsupported | Pre-history; no fixes. Upgrade to `0.2.x` immediately.               |
| Development milestone tags (`release-1.0-alpha`, `release-1.0`, `release-2.0`) | Best effort | Internal development milestones, not distributed releases; upgrade to `main` instead. |
| Any PyPI/npm release claiming a stable version | No such release exists at the time of writing; treat one as unofficial. | — |

## Reporting a Vulnerability

**Do not open a public GitHub issue, discussion, or pull request for a
suspected vulnerability, and do not publicly disclose it before a fix ships.**

Report privately through GitHub's private vulnerability reporting:

1. Go to <https://github.com/aryansinghnagar/JoBot/security/advisories/new>
2. Submit a description, reproduction steps, and impact assessment

Please include, where applicable:

- Steps to reproduce (commands, configuration, sample inputs)
- Affected component (CLI, `jobot sidecar`, GUI shell, adapter, vault/keyring
  handling, plugin system, CI)
- JoBot revision (`jobot --version` output or git commit hash)
- Whether any secret material was reachable

What to expect:

- **Acknowledgement target:** within 72 hours of the report (this is a target
  maintained by a single maintainer, not a contractual SLA).
- **Triage target:** initial assessment and severity rating within 7 days.
- **Fix process:** fixes land on `main`; coordinated disclosure and a GitHub
  security advisory are published once a fix is available.
- Public CVE/request where appropriate for externally introduced dependencies.

Please report third-party dependency advisories you believe are exploitable
*through JoBot*; for advisories that are already tracked (see residuals below
and `MASTER_PLAN_EXPANDED.md` Section 2.2), a report is only needed if you
have an exploit path that is not already documented.

## Known Accepted Residuals

The project tracks its full vulnerability set in `MASTER_PLAN_EXPANDED.md`
Section 2.2 and risk register R17 (Section 7). The following residuals are
explicitly accepted and documented rather than fixed:

### 1. `glib` RUSTSEC-2024-0429 (transitive via Tauri 2) — accepted

- **Advisory:** RUSTSEC-2024-0429 / GHSA-wrw7-89jp-8q8g (glib function
  interception issue).
- **Path:** the desktop GUI shell in `gui/src-tauri` is built on Tauri 2,
  which transitively depends on the vulnerable `glib` crate. There is **no
  in-tree fix** available while staying on Tauri 2.
- **Scope:** affects Rust/GTK builds of the desktop shell (Linux GTK-linked
  builds primarily). The Python core, CLI, and sidecar do not link glib
  through this path.
- **Decision:** accepted as a documented residual — decision **D3** in
  `MASTER_PLAN_EXPANDED.md` Section 5 (decided 2026-08-16).
- **Revisit trigger:** migration to Tauri >= 3 / gtk4 (D3 escalation), plus
  cargo Dependabot/audit monitoring (R17 mitigation).
- **User guidance:** users who do not build or run the Tauri desktop shell
  (`npm run tauri:dev` / `npm run tauri:build`) are not exposed to this
  dependency; the CLI and sidecar surfaces do not require it.

### 2. Live browser adapters are opt-in and never defeat anti-bot controls

- Live-browser automation for site adapters (LinkedIn, Naukri, Workday, and
  others) is **disabled by default** and only enabled when the environment
  variable `JOBOT_RUN_LIVE_BROWSER=1` is set. With the flag unset, adapters
  return honest "live browser disabled" no-op results and never fabricate a
  submission (see `src/jobot/adapters/linkedin.py`,
  `src/jobot/adapters/naukri/adapter.py`, `src/jobot/adapters/workday.py`).
- Defeating platform anti-bot controls (CAPTCHA solving at scale, bot
  detection evasion, bulk high-volume apply) is an explicit **non-goal** of
  this project (`MASTER_PLAN_EXPANDED.md` Section 2.4, Non-goals v1). The
  project takes a conservative Terms-of-Service stance toward LinkedIn and
  job boards; risky-feature ideas require `JOBOT_ENABLE_RISKY=1` plus
  per-feature flags (decision D12) and hard caps remain even when enabled
  (D24).
- Residual accepted: users who enable live-browser mode do so at their own
  risk with respect to platform ToS; the software provides rate caps and
  human-approval defaults (D15: submission autonomy is human-by-default) but
  does not promise account safety on third-party platforms.

Additional tracked-but-unresolved items (vite/esbuild/nanoid advisory set,
CodeQL `py/incomplete-url-substring-sanitization` alerts) are enumerated in
`MASTER_PLAN_EXPANDED.md` Section 2.2 with remediation workstreams in WS1;
they are handled as normal security work, not permanent acceptances.

## Secure Configuration Guidance

Secrets handling in JoBot is layered; keep it that way:

- **API keys and credentials belong in the OS keyring, never in files.**
  `jobot config set <key> <value>` routes secret values into the OS keyring
  (service `jobot`, see `src/jobot/secrets.py`); `jobot config show`/`get`
  mask them. `.env` holds non-secret runtime configuration only.
- **Credential vault:** `src/jobot/storage/vault.py` (`CredentialVault`)
  encrypts profiles with Fernet (AES-256). The master key is stored in the OS
  keyring (service `jobot_vault`). If the keyring is unavailable, the master
  key falls back to a keyfile at `~/.jobot/vault/master.key`, which JoBot
  restricts to `0600` on POSIX systems.
  - If you run on the keyfile fallback, verify with `ls -l` that
    `~/.jobot/vault/master.key` (and `~/.jobot/profiles/*.enc`) are readable
    only by your user; on Windows, restrict the `%USERPROFILE%\.jobot`
    directory to your account.
  - Never copy, commit, or back up the vault master key alongside encrypted
    data; never share a machine account running JoBot with untrusted users.
- **Logging:** JoBot masks secret values in CLI output (`mask()` keeps at
  most a 4-character prefix). Do not paste raw secrets into bug reports,
  logs, or screenshots — redact before attaching (see the bug report
  template).
- **Human approval is the default for real submissions** (decision D15);
  auto-submit modes exist but are opt-in and capped by the policy engine.
  Prefer `--dry-run` while evaluating the system.

## Prompt-Injection Surface & Input Sanitization
 
 Job descriptions, search results, scraped page content, and any text sourced
 from third-party sites are **untrusted content**. They are passed through
 LLM-powered tailoring, matching, and question-answering steps.
 
1. **Active Prompt Guard (`src/jobot/security/prompt_guard.py`)**:
   All external text (job titles, descriptions, candidate questions) passes through
   regular expression sanitizers that neutralize instruction overrides, role-switch attempts
   (e.g., `you are now a...`, `act as a...`), prompt exfiltration queries, and delimiter tags
   before entering LLM prompts.
2. **Candidate Grounding Gate (`CandidateGroundingVerifier`)**:
   LLM output is strictly validated against the candidate's truth ledger before inclusion
   in resumes or cover letters. Unverified skills, employers, or dates cause immediate rejection.
3. **Candidate Data Flow & PII Disclosure**:
   - During resume tailoring and cover letter generation, candidate name, contact info,
     experience descriptions, education, and skills are sent to the configured LLM provider.
   - API keys are injected server-side by HTTP provider classes and never embedded in prompt bodies.
   - Users can choose local inference (via Ollama) if zero cloud PII transmission is required.
4. **Human Review Before Submission**:
   Users should review generated materials and form fields in the Approval Inbox before
   authorizing submission. If an adversarial job description bypasses sanitization, human
   verification ensures no unauthorized claims are submitted.

## Supply-Chain Policy

- **CI actions:** GitHub Actions used in `.github/workflows/` must be pinned
  to the most restrictive ref that is practical; when adding or updating a
  workflow step, pin third-party actions to a **full commit SHA** (this is
  the target policy — the existing workflows currently pin to major-version
  tags, and the migration is tracked as WS1 W4 in `MASTER_PLAN_EXPANDED.md`).
  Workflow `permissions` blocks are required and set to least privilege
  (e.g. `contents: read`).
- **Dependency updates:** Dependabot is enabled for the repository; CodeQL
  scanning runs on pushes and pull requests. Known advisories are triaged
  against the set documented in Section 2.2 of the expanded master plan.
- **Plugins are deny-by-default.** The plugin system
  (`src/jobot/plugins/`) validates a manifest against fixed allowlists:
  only declared permission categories in `ALLOWED_PERMISSIONS`, only
  allowlisted packages in `ALLOWED_REQUIRES`, and entrypoints may never live
  in forbidden internal modules (`jobot.storage.vault`, `jobot.secrets`,
  `jobot.config`). Installation runs a static audit (permissions,
  dependencies, entrypoints, secret-pattern scan) with **no execution of
  plugin code**; anything outside the allowlists is rejected.
- **No telemetry by default.** The application is local-first; no crash
  reporting or analytics leave the machine unless explicitly enabled.
- **Secrets never enter the repository.** History has been verified with
  gitleaks; keep it that way — see `CONTRIBUTING.md` for the "no secrets in
  diff" checklist item on every pull request.

## Scope of This Policy

The core Python system is licensed AGPL-3.0-only and site adapters are MIT
(see `LICENSE` and `README.md`). This policy covers the entire repository,
including the Tauri desktop shell in `gui/` and the JSON-RPC sidecar.
