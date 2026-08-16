# Runtime Capability Matrix — AJOS

| Capability | Initial Target (dev-0.1) | Production Target (release-1.0) | Status | Notes |
|---|---|---|---|---|
| **OS Support** | Windows (Dev), Linux | Windows, Linux, macOS | Planned | Windows is primary packaging target |
| **CLI Engine** | Typer CLI | Typer CLI + Full Command Suite | In Progress | `setup`, `profile`, `run`, `status`, `pause`, `export` |
| **GUI Engine** | CLI only | Tauri 2.x + React + Vanilla CSS | Deferred to dev-3.0 | Local IPC over JSON-RPC |
| **Database** | SQLite WAL | SQLite WAL (Encrypted) | Planned | DB file `~/.jobaut/jobaut.db`, mode 0600 |
| **Vault / Secrets** | `age` + Keyring / file | `age` + OS Keyring (Win Credential Mgr / SecretService) | In Progress | Zero secrets in git/logs |
| **Browser Engine** | Patchright (Chromium) | Patchright + Camoufox + CDP Fallback | In Progress | Anti-detection & fingerprint randomization |
| **LLM Provider** | Profile-direct (dev-0.1) / Gemini | Gemini primary (`google-genai`), OpenAI/Anthropic/Ollama fallback | Planned | Provider-neutral `ModelRouter` |
| **Supported Sites** | Mock ATS + Naukri | 25+ Sites (Naukri, LinkedIn, Indeed, Workday, etc.) | In Progress | SiteAdapter contract |
| **ASP State Machine** | 12-Phase Pipeline | 12-Phase Pipeline with auto-recovery | In Progress | Idempotency + DoD validation |
| **Stealth & Anti-Bot** | Rate jittering, stealth headers | Proxies, Bezier mouse, keystroke dynamics, CAPTCHA solver | Planned | Configurable per site |
