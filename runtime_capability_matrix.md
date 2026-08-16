# Runtime Capability Matrix — AJOS

| Capability | Initial Target (dev-0.1) | Production Target (release-1.0) | Refactor Status | Notes |
|---|---|---|---|---|
| **OS Support** | Windows (Dev), Linux | Windows, Linux, macOS | Planned | Windows is primary packaging target |
| **CLI Engine** | Typer CLI | Typer CLI + Full Command Suite | Real | `setup`, `profile`, `run`, `status`, `pause`, `export`, `continuous-campaign` |
| **GUI Engine** | CLI only | Tauri 2.x + React + Vanilla CSS | Deferred to release-2.0 | Stdio JSON-RPC sidecar protocol implemented |
| **Database** | SQLite WAL | SQLite WAL | Real | DB file `~/.jobot/jobot.db`, mode 0600 |
| **Vault / Secrets** | Fernet + Keyring / file | Fernet + OS Keyring (Win Credential Mgr / SecretService) | Real | Zero secrets in git/logs |
| **Browser Engine** | Patchright (Chromium) | Patchright (Release 1.0) | In Progress | Patchright integration in progress for Naukri adapter |
| **LLM Provider** | Gemini | Gemini primary, OpenAI/Anthropic/Ollama fallback | In Progress | Provider-neutral `ModelRouter` fallbacks in progress |
| **Supported Sites** | Mock ATS + Naukri | Naukri (Patchright) + Greenhouse (API) | In Progress | 2 real adapters for Release 1.0; remaining stubs queued for Release 1.1/2.0 |
| **ASP State Machine** | 12-Phase Pipeline | 12-Phase Pipeline with strict DoD validation | In Progress | Idempotency + DoD validation in progress |
| **Stealth & Anti-Bot** | Rate jittering | Bezier mouse, keystroke dynamics, CAPTCHA solver | In Progress | BehavioralMimicry Bezier fix in progress |
