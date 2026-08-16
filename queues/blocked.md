# BLOCKED QUEUE — Waiting on Human/Environment

## Owner decisions (MASTER_PLAN.md §19 — safe defaults already chosen)

1. **D15 submission autonomy default** — confirm human-approval-by-default with trusted-site promotion. Blocks only ToS-risk scope (F-19/21), not v1.0.
2. **D5/D6 signing** — SignPath OSS enrollment (Windows) + macOS notarization budget vs documented Gatekeeper workaround. Blocks WS9 signing steps only.
3. **Geographic adapter priority** — India-first vs US/EU-first live-validation order (post-v1 scheduling input).
4. **W10 manual repo settings** — secret-scanning push protection, Dependabot security updates, branch protection on `main` (needs repo admin).

## Environment blockers

- [ ] Windows C toolchain (MinGW `dlltool` or MSVC `link.exe`) for local `cargo check` / `tauri:dev` — desktop CI (`desktop.yml`) will close this independently.
- [ ] Live LLM degraded on dev machine (gemini OAuth 401) — degradation paths verified truthful; full live validation pending credentials.

## Resolved archive

Review-2 findings P0.1–P0.5, P1.7–P1.10, P2.6 all RESOLVED (see git history); premature `release-1.0` tag retracted and re-earned.
