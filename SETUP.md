# JoBot Setup Guide

**Version:** Draft 1.0 · 2026-08-13
**Target:** [aryansinghnagar/JoBot](https://github.com/aryansinghnagar/JoBot)
**Companion document:** [PLAN.md](./PLAN.md) (architecture + merge plan) · [JoBot_Merge_Plan.pdf](./JoBot_Merge_Plan.pdf) (127-page full version)

---

## Table of Contents

1. [Prerequisites & System Requirements](#1-prerequisites--system-requirements)
2. [Local Dev Installation](#2-local-dev-installation)
3. [Configuration & Secrets](#3-configuration--secrets)
4. [AI Provider API Keys](#5-ai-provider-api-keys-all-6-supported-providers)
5. [Docker Setup](#6-docker-setup)
6. [Desktop GUI (Release 2.0)](#7-desktop-gui-release-20)
7. [CLI Reference](#8-cli-reference)
8. [Troubleshooting & FAQ](#9-troubleshooting--faq)

---

## 1. Prerequisites & System Requirements

### Hard Prerequisites

| Component | Version | Why needed | Verify |
|---|---|---|---|
| Python | 3.11+ | PEP 695 type aliases, match-case, async improvements | `python3 --version` |
| pip | 23.0+ | Package installation | `pip --version` |
| git | 2.20+ | Cloning the repo | `git --version` |
| OS keyring | Any | API key + secret storage | `python3 -c "import keyring; print(keyring.get_keyring())"` |
| At least one LLM API key | — | Default: Google Gemini (free tier sufficient) | See [§5](#5-ai-provider-api-keys-all-6-supported-providers) |

### Soft Prerequisites

| Component | Version | Why needed | Install |
|---|---|---|---|
| LaTeX engine | TeX Live 2023+ or Tectonic 0.5+ | Resume PDF generation | macOS: `brew install --cask mactex-no-gui` or `brew install tectonic`; Linux: `apt install texlive-full` or `snap install tectonic` |
| poppler-utils | 20+ | `pdftotext` for ATS parseability check | macOS: `brew install poppler`; Linux: `apt install poppler-utils` |
| Playwright system deps | — | Browser automation | `patchright install-deps` |
| Docker | 24+ | Containerized deployment | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2+ | Container orchestration | Bundled with Docker Desktop; Linux: `apt install docker-compose-plugin` |

### OS Support Matrix

| OS | Support level | Notes |
|---|---|---|
| macOS (Intel) | Tier 1 — fully tested | Use Homebrew. Patchright works natively. |
| macOS (Apple Silicon) | Tier 1 — fully tested | Same as Intel. |
| Linux (Ubuntu 22.04+) | Tier 1 — fully tested | Best Docker experience. gnome-keyring recommended. |
| Linux (Debian 12+) | Tier 1 — fully tested | Same as Ubuntu. |
| Linux (Fedora 39+) | Tier 2 — should work | Not in CI. |
| Linux (Arch) | Tier 3 — community-supported | Works but not in CI. |
| Windows 10/11 (native) | Tier 3 — works with WSL2 | WSL2 strongly recommended. |
| Windows 10/11 (WSL2) | Tier 1 — fully tested | Best Windows experience. |

### Resource Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| Disk | 2 GB | 10 GB |
| CPU | Any modern dual-core | Quad-core+ |
| Network | Broadband | Broadband |

---

## 2. Local Dev Installation

### 2.1 macOS (Intel & Apple Silicon)

```bash
# Step 1: Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew --version  # → Homebrew 4.x.x

# Step 2: Install Python 3.11, poppler, Tectonic
brew install python@3.11 poppler
brew install tectonic  # lightweight LaTeX alternative

# Step 3: Clone JoBot
git clone https://github.com/aryansinghnagar/JoBot.git
cd JoBot

# Step 4: Create venv + install
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'

# Step 5: Install Patchright browser
patchright install chromium
patchright install-deps

# Step 6: Initialize JoBot
jobot init
# → Creates ~/.jobot/ directory with default profile.yaml
# → Prompts for Gemini API key (stored in macOS Keychain)

# Step 7: Verify
jobot doctor
# Expected:
# ✓ Python 3.11.x
# ✓ SQLite 3.x
# ✓ OS keyring: macOS Keychain
# ✓ Patchright browser installed
# ✓ LaTeX engine: lualatex
# ✓ pdftotext available
# ✓ LLM provider 'gemini' configured and reachable
# JoBot is ready.
```

### 2.2 Linux (Ubuntu 22.04+)

```bash
# Step 1: Install Python + system deps
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
                    poppler-utils git build-essential \
                    gnome-keyring  # for keyring integration
# Optional: full TeX Live (large download) or lightweight Tectonic
sudo apt install -y texlive-full
# Or:
sudo snap install tectonic

# Step 2: Clone + venv + install
git clone https://github.com/aryansinghnagar/JoBot.git
cd JoBot
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
patchright install chromium
patchright install-deps

# Step 3: Initialize gnome-keyring (headless server only)
eval $(gnome-keyring-daemon --start)
export SSH_AUTH_SOCK
# Add to ~/.bashrc for persistence

# Step 4: jobot init + jobot doctor (same as macOS)
```

### 2.3 Windows 10/11 with WSL2 (Recommended)

```powershell
# In PowerShell (admin):
wsl --install -d Ubuntu-22.04
# Restart, set Ubuntu user/password when prompted
# Open Ubuntu shell
```

Inside Ubuntu shell, follow the Linux steps (§2.2). For interactive browser sessions on WSL2:

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0.0
# Requires VcXsrv or similar X server running on Windows
```

### 2.4 Windows Native (Not Recommended)

JoBot works on native Windows but the setup is more painful. Use WSL2 instead. If you must use native Windows: install Python 3.11+ from python.org, Git from git-scm.com, MiKTeX from miktex.org, then follow the macOS-equivalent steps.

---

## 3. Configuration & Secrets

JoBot uses a three-tier config system:

### Tier 1 — `.env` (Runtime Config, safe to log)

```bash
# .env — runtime config (NEVER put API keys here!)
JOBOT_ENV=development                    # development | production
JOBOT_LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR
JOBOT_PROFILE=default                    # which profile to use
JOBOT_DATA_DIR=~/.jobot/data             # SQLite + blobs
JOBOT_BROWSER_PROFILE_DIR=~/.jobot/browser-profiles
JOBOT_EVIDENCE_DIR=~/.jobot/evidence     # screenshots
JOBOT_CACHE_DIR=~/.jobot/cache           # salary lookups, etc.
JOBOT_DEFAULT_LLM_PROVIDER=gemini
```

### Tier 3 — OS Keyring (API Keys & Master Key)

All API keys live in OS keyring, accessed via `keyring.get_password('jobot', <key>)`. Use `jobot config set` to write — never edit a file directly.

```bash
# Set Gemini API key (default provider):
jobot config set llm.api_key.gemini AIzaSy...

# Set OpenAI API key (for fallback chain):
jobot config set llm.api_key.openai sk-proj-...

# Set Anthropic API key:
jobot config set llm.api_key.anthropic sk-ant-...

# Set OpenRouter (OpenAI-compatible):
jobot config set llm.api_key.openrouter sk-or-...

# Set LinkedIn cookies (for browser session reuse — optional):
jobot config set board_cookies.linkedin 'li_session=...; li_at=...'

# Set SMTP credentials (for digest email):
jobot config set smtp.user your-email@gmail.com
jobot config set smtp.password your-app-password

# Verify config:
jobot config show
# → Lists all keys (values masked: 'AIzaSy***')

# Get a specific value:
jobot config get llm.api_key.gemini
# → AIzaSy...
```

### Tier 2 — `secrets.yaml` (Encrypted Board Credentials)

```bash
# Edit secrets.yaml (jobot decrypts on open, re-encrypts on save):
jobot secrets edit
```

```yaml
# secrets.yaml (decrypted view in $EDITOR)
board_credentials:
  linkedin:
    email: you@example.com
    # password in OS keyring as 'board_password.linkedin'
  greenhouse:
    api_token: gh-...
  workday_custom:
    username: you@example.com
    password_env: WORKDAY_PASSWORD   # reads from env at apply time

smtp:
  host: smtp.gmail.com
  port: 465
  # credentials in OS keyring as 'smtp.user' and 'smtp.password'

scheduler:
  daily_apply_cap: 50
  weekly_apply_cap: 200
  daily_cost_cap_usd: 5.00
```

### Tier 4 — Profiles (User Personas)

```yaml
# profiles/default.yaml — default user profile
identity:
  name: Aryan Singh Nagar
  email: aryansinghnagar@example.com
  phone: "+1-555-0100"
  location: "San Francisco, CA"
  linkedin_url: https://linkedin.com/in/aryansinghnagar
  github_url: https://github.com/aryansinghnagar

search:
  keywords: ["senior backend engineer", "distributed systems", "python"]
  location: "San Francisco Bay Area"
  sites: [linkedin, greenhouse, lever, indeed]
  remote_only: false
  visa_sponsor_required: false

target:
  min_salary_usd: 180000
  min_role_level: senior
  blacklisted_companies: []
  blacklisted_keywords: ["on-call", "weekend work"]

resume_base:
  summary: |
    Senior backend engineer with 8 years building distributed systems at scale.
  skills: [Python, Go, Kubernetes, PostgreSQL, Redis, Kafka, AWS, GCP, Terraform]
  experience:
    - company: Stripe
      title: Senior Software Engineer
      dates: "2022-Present"
      bullets:
        - "Led redesign of payment reconciliation service; P99 latency 4.2s→180ms."
        - "Owned migration from monolith to event-driven microservices (Kafka+Go)."
    - company: Airbnb
      title: Software Engineer
      dates: "2018-2022"
      bullets:
        - "Built search ranking pipeline serving 50M queries/day."
  education:
    - degree: "B.S. Computer Science"
      school: "UC Berkeley"
      year: 2018

llm:
  default_provider: gemini
  fallback_chain: [gemini, openai, anthropic]
  daily_cost_cap_usd: 5.00
  task_overrides:
    resume_tailoring:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
    question_answering:
      provider: gemini
      model: gemini-2.0-flash

outreach:
  presets: [faang_senior_backend, startup_founding_eng]
  daily_dm_cap: 5
```

### Config Wizard

`jobot init` runs an interactive wizard on first invocation. Creates `~/.jobot/`, prompts for identity + search + target fields, generates `profiles/default.yaml`, prompts for at least one LLM API key. Restartable — answer 'skip' to any field.

---

## 5. AI Provider API Keys (All 6 Supported Providers)

JoBot supports six provider classes with twelve concrete instances. **Google Gemini is the default** — out of the box, with only `GEMINI_API_KEY` set, JoBot works.

### 5.1 Google Gemini (DEFAULT — Required for First Run)

- **Where:** [Google AI Studio](https://aistudio.google.com/apikey) — sign in with Google, click 'Create API Key'
- **Set:**
  ```bash
  jobot config set llm.api_key.gemini AIzaSy...
  ```
- **Free tier:** 15 RPM, 1500 RPD, 1M tokens/minute
- **Default model:** `gemini-2.0-flash` — $0.075/1k input, $0.30/1k output
- **Cost:** ~$0.005 per resume + cover letter

### 5.2 OpenAI

- **Where:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys) (no free tier)
- **Set:**
  ```bash
  jobot config set llm.api_key.openai sk-proj-...
  ```
- **Recommended model:** `gpt-4o-mini` (most tasks) or `gpt-4o` (resume tailoring)
- **Cost:** GPT-4o-mini: $0.150/1k input + $0.600/1k output. GPT-4o: $2.50/1k input + $10/1k output

### 5.3 Anthropic Claude

- **Where:** [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
- **Set:**
  ```bash
  jobot config set llm.api_key.anthropic sk-ant-api03-...
  ```
- **Recommended model:** `claude-3-5-sonnet-20241022` for resume tailoring (highest-quality tailored resumes)
- **Cost:** Claude 3.5 Sonnet: $3/1k input + $15/1k output. Claude 3 Haiku: $0.25/1k input + $1.25/1k output

### 5.4 OpenAI-Compatible (OpenRouter, Groq, Together, Ollama, vLLM)

All five speak the OpenAI Chat Completions API. JoBot uses a single `OpenAICompatProvider` class parameterized by `base_url` + `api_key`.

| Provider | Base URL | Env var | Free tier? |
|---|---|---|---|
| OpenRouter | https://openrouter.ai/api/v1 | `OPENROUTER_API_KEY` | Free models available |
| Groq | https://api.groq.com/openai/v1 | `GROQ_API_KEY` | Yes — 30 RPM, 14400 RPD |
| Together | https://api.together.xyz/v1 | `TOGETHER_API_KEY` | $5 free credit |
| Ollama (local) | http://localhost:11434/v1 | `OLLAMA_BASE_URL` | Free (self-hosted) |
| vLLM (local) | Set via env | `VLLM_BASE_URL` | Free (self-hosted) |

```bash
# OpenRouter:
jobot config set llm.api_key.openrouter sk-or-...
jobot config set llm.base_url.openrouter https://openrouter.ai/api/v1

# Groq:
jobot config set llm.api_key.groq gsk_...
jobot config set llm.base_url.groq https://api.groq.com/openai/v1

# Ollama (local — install from ollama.com first):
ollama pull llama3.1:8b
ollama serve  # runs at http://localhost:11434
jobot config set llm.base_url.ollama http://localhost:11434/v1
jobot config set llm.api_key.ollama dummy   # no key needed
jobot config set llm.default_provider ollama   # fully offline mode
```

### 5.5 Mistral

- **Where:** [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys)
- **Set:**
  ```bash
  jobot config set llm.api_key.mistral <your-key>
  ```
- **Free tier:** 1 RPS, 500K tokens/month
- **Recommended model:** `mistral-large-latest` — $2/1k input + $6/1k output

### 5.6 Cohere

- **Where:** [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys)
- **Set:**
  ```bash
  jobot config set llm.api_key.cohere <your-key>
  ```
- **Free tier:** Trial key, 1000 calls/month
- **Recommended model:** `command-r-plus-08-2024` — $2.50/1k input + $10/1k output
- **Use case:** also useful for embeddings (text-embedding-3-small) — alternative to Gemini's embedding API for the vector-memory dedup layer

### 5.7 AWS Bedrock (Enterprise)

Bedrock is the enterprise path — auth via IAM, no API key file.

```bash
# Standard AWS credentials flow:
aws configure
# → AWS Access Key ID: AKIA...
# → AWS Secret Access Key: ...
# → Default region: us-east-1

# JoBot reads from standard AWS_* env vars:
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1

# Grant Bedrock model access in AWS console:
# Bedrock → Model access → Manage model access →
#   enable Anthropic Claude, Mistral, etc.

# Use Bedrock as default:
jobot config set llm.default_provider bedrock
jobot config set llm.default_model anthropic.claude-3-5-sonnet-20241022-v2:0
```

### 5.8 Google Vertex AI (Enterprise)

Vertex AI is Google Cloud's enterprise LLM platform — same Gemini models but via GCP auth.

```bash
# Create a service account in GCP:
# IAM → Service accounts → Create service account →
#   name: jobot-sa
#   roles: Vertex AI User
# → Create JSON key → download as jobot-sa-key.json

# Tell JoBot where the key is:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/jobot-sa-key.json
export VERTEX_PROJECT=my-gcp-project-id
export VERTEX_REGION=us-central1

# Use Vertex as default:
jobot config set llm.default_provider vertex
jobot config set llm.default_model gemini-1.5-pro-002
```

### 5.9 Switching Providers at Runtime

```bash
# Switch default provider:
jobot config set llm.default_provider anthropic
# Next LLM call will use Anthropic

# Switch for a specific task only (per-profile YAML):
# In profiles/default.yaml:
llm:
  default_provider: gemini
  task_overrides:
    resume_tailoring:
      provider: anthropic              # use Claude for resumes
      model: claude-3-5-sonnet-20241022
    question_answering:
      provider: gemini                # cheap model for form Q&A
      model: gemini-2.0-flash

# Force a specific provider for a single CLI invocation:
jobot --provider anthropic apply <job-id>
```

---

## 6. Docker Setup

Docker is the recommended deployment path for production. The compose stack has three services: `jobot` (app), `jobot-scheduler` (cron), and optionally `jobot-db` (Postgres for >10k jobs scale).

### 6.1 Dockerfile (Multi-Stage)

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils gnupg fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
# Tectonic (lightweight LaTeX)
RUN curl -fsSL https://drop-sh.fullyjustified.net | sh && \
    mv tectonic /usr/local/bin/
# Patchright browser
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl patchright && \
    patchright install chromium && \
    patchright install-deps && \
    rm /tmp/*.whl
RUN mkdir -p /data /browser-profile /evidence /cache
VOLUME ["/data", "/browser-profile", "/evidence", "/cache"]
ENV JOBOT_DATA_DIR=/data \
    JOBOT_BROWSER_PROFILE_DIR=/browser-profile \
    JOBOT_EVIDENCE_DIR=/evidence \
    JOBOT_CACHE_DIR=/cache
WORKDIR /app
ENTRYPOINT ["jobot"]
CMD ["--help"]
```

### 6.2 docker-compose.yml

```yaml
version: '3.9'

services:
  jobot:
    build: .
    image: jobot:latest
    container_name: jobot
    restart: unless-stopped
    env_file: .env
    volumes:
      - jobot-data:/data
      - jobot-browser-profile:/browser-profile
      - jobot-evidence:/evidence
      - jobot-cache:/cache
      - ./profiles:/app/profiles:ro
    secrets:
      - source: jobot_keyring
        target: /run/secrets/keyring
    healthcheck:
      test: ["CMD", "jobot", "doctor"]
      interval: 5m
      timeout: 30s
      retries: 3
      start_period: 30s

  jobot-scheduler:
    image: jobot:latest
    container_name: jobot-scheduler
    restart: unless-stopped
    env_file: .env
    depends_on:
      jobot:
        condition: service_healthy
    volumes:
      - jobot-data:/data:ro
      - jobot-browser-profile:/browser-profile
      - ./profiles:/app/profiles:ro
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        echo '0 9 * * * jobot loop full-loop --profile default --max-apply 10' > /etc/cron.d/jobot
        echo '0 8 * * 1 jobot loop digest --profile default' >> /etc/cron.d/jobot
        echo '0 0 * * * jobot policy reset-daily --profile default' >> /etc/cron.d/jobot
        crontab /etc/cron.d/jobot
        crond -f

volumes:
  jobot-data:
  jobot-browser-profile:
  jobot-evidence:
  jobot-cache:

secrets:
  jobot_keyring:
    file: ./secrets/keyring.enc
```

### 6.3 Bring Up the Stack

```bash
# 1. Create .env from template
cp .env.example .env
# Edit .env: set JOBOT_PROFILE, JOBOT_DEFAULT_LLM_PROVIDER, etc.

# 2. Set API keys via the in-container keyring (one-time):
docker compose run --rm jobot config set llm.api_key.gemini AIzaSy...
docker compose run --rm jobot config set llm.api_key.openai sk-proj-...

# 3. Build + start the stack:
docker compose up -d --build
# Expected: 2 containers running (jobot + jobot-scheduler)

# 4. Verify:
docker compose exec jobot jobot doctor
# Expected: all checks pass

# 5. Run a manual scrape test:
docker compose exec jobot jobot scrape linkedin --keywords 'senior backend' --limit 10

# 6. View scheduler logs:
docker compose logs -f jobot-scheduler
```

### 6.4 Secrets Management in Docker

The container has no OS keyring by default. JoBot uses a fallback keyring backend that reads from an encrypted file at `/run/secrets/keyring` (the Docker secret). This file is encrypted with a master key derived from `JOBOT_DOCKER_MASTER_KEY` env var.

```bash
# On host (one-time setup):
echo "$(openssl rand -hex 32)" > .docker-master-key
echo "JOBOT_DOCKER_MASTER_KEY=$(cat .docker-master-key)" >> .env
rm .docker-master-key
# .docker-master-key is gone — only the env var (in .env, .gitignore'd) knows it.

# First container run creates the encrypted keyring file:
docker compose run --rm jobot config set llm.api_key.gemini AIzaSy...
```

### 6.5 Backup Strategy

```bash
# Host crontab — backup the data volume nightly:
0 2 * * * docker run --rm -v jobot-data:/data -v /backups:/backups \
    alpine tar czf /backups/jobot-data-$(date +\%F).tar.gz /data
# Retention: keep last 30 days
0 3 * * * find /backups -name 'jobot-data-*.tar.gz' -mtime +30 -delete
```

---

## 7. Desktop GUI (Release 2.0)

JoBot ships a desktop GUI: a Tauri 2 + React 18 shell in `gui/` that talks to
the backend over the `jobot sidecar` JSON-RPC bridge (line-delimited JSON-RPC
2.0 on stdio). The Rust shell is intentionally thin — it only spawns the
`jobot sidecar` process; all logic stays in the Python core.

### 7.1 Prerequisites

| Component | Version | Why needed |
|---|---|---|
| Node.js | 18+ | Vite build + vitest + prettier |
| Rust toolchain | 1.77+ | Tauri 2 shell (only for `tauri:dev` / `tauri:build`) |
| Windows C toolchain | MinGW (`dlltool`) or MSVC (`link.exe`) | Linking the Tauri shell on Windows |

The JS gates (`npm run test`, `npm run lint`, `npm run build:gui`) run on
Node only and are part of CI. The Rust/Tauri build is **local-only** and is
not gated in CI.

### 7.2 Install & Run

```bash
# JS deps live in the ROOT package.json (single npm ci for CI):
npm ci

# Headless verification (CI gates):
npm run test        # vitest — tests/npm + gui/tests
npm run lint        # prettier --check
npm run build:gui   # vite build → gui/dist

# Desktop app (dev — hot reload):
npm run tauri:dev   # requires Rust toolchain + Windows C linker

# Production bundle:
npm run tauri:build
```

The GUI shows a sidecar-unavailable message instead of crashing when the
`jobot` console script is not installed or the sidecar fails to spawn.

## 8. CLI Reference

All commands are subcommands of `jobot`. Common flags: `--profile <name>`, `--json`, `--dry-run`.

### Initialization & Diagnostics

| Command | Purpose |
|---|---|
| `jobot init` | First-run setup wizard |
| `jobot doctor` | Verify environment |
| `jobot --version` | Print version + git commit hash |
| `jobot --help` | List all subcommands |

### Configuration & Secrets

| Command | Purpose |
|---|---|
| `jobot config get <key>` | Get a config value (masked if secret) |
| `jobot config set <key> <value>` | Set a config value (secrets → OS keyring) |
| `jobot config show` | List all config (secrets masked) |
| `jobot config unset <key>` | Remove a config value |
| `jobot config reload` | Force re-instantiation of all providers |
| `jobot secrets edit` | Open $EDITOR on decrypted secrets.yaml |
| `jobot policy reset-daily` | Reset daily caps (cron at midnight UTC) |

### Scraping & Discovery

> **Phase 2**: `jobot scrape` runs against **real feeds only** — never
> fabricated postings. Job boards (linkedin, indeed, glassdoor, google,
> zip_recruiter, bayt, naukri, bdjobs) are scraped via the `python-jobspy`
> library; ATS boards (greenhouse, lever, ashby, smartrecruiters) hit the
> vendor's public JSON API directly; `careers` fingerprints company career
> pages (see `src/jobot/scrapers/career_sites.yaml`) and dispatches to the
> matching ATS API; `mock_ats` targets the local test server on port 5800.

| Command | Purpose |
|---|---|
| `jobot scrape <board> [--keywords --location --limit --companies --json --no-dedup --hours-old --country --save]` | Scrape real postings from one board with two-tier dedup (exact hash + vector cosine ≥ 0.92); `--save` persists postings to the database for `jobot apply` |
| `jobot scrape --all` | Scrape every available board in sequence |
| `jobot scrape careers --companies webflow,figma` | Fingerprint and scrape ATS career pages for given companies |
| `jobot scrape lever --companies toptal` | Scrape a company's Lever/Ashby/SmartRecruiters public feed |
| `jobot dedup [--stats]` | Show the persistent dedup cache state |

**Installing the scraper library (optional extra):** the `python-jobspy`
package cannot be a declared dependency — its metadata pins `NUMPY==1.26.3`,
which does not resolve on Python ≥ 3.12. Install it with the documented
`--no-deps` recipe and let the `[scrapers]` extra provide the runtime deps:

```sh
pip install -e '.[scrapers]'
pip install python-jobspy==1.1.82 --no-deps   # import name is still `jobspy`
```

Without it, JobSpy boards fail with a clear `JobSpyNotInstalledError` message
pointing to this recipe; ATS/careers/mock_ats boards work without it.

**Politeness config** (`jobot config set`): `scraper.jobspy.delay_s` (seconds
between scrapes, default 1.0) and `scraper.jobspy.proxy_list`
(comma-separated proxies, optional). LinkedIn applies aggressive per-IP rate
limits — keep the delay, consider proxies for high-volume runs.

### Ranking & Applying

> **Phase 3**: `jobot apply` runs the full document stack: tailored resume PDF
> (ATS-scored ≥ 0.85), cover letter, then the 12-phase pipeline under a saga.
> Supervised by default (stops for approval at phase 10) unless `--approve`.
> `--dry-run` produces the artifacts without submitting.

| Command | Purpose |
|---|---|
| `jobot rank` | Score and rank saved jobs |
| `jobot apply <job-id> [--url --site] [--dry-run --approve --resume <saga> --template --tone --extra-prompt --engine]` | Tailor documents and submit via the saga orchestrator |
| `jobot apply --resume <saga-id> --approve` | Resume an interrupted apply saga |
| `jobot tracker list` | List applications (kanban via rich tables) |
| `jobot tracker show <job-id>` | Show application detail |
| `jobot tracker move <job-id> <status>` | Manually move to a new ASP state |

### Resume & Cover Letter

| Command | Purpose |
|---|---|
| `jobot resume [action]` | No action = resume paused loops (unchanged); `tailor` = drafter→reviewer loop → tailored PDF + ATS score; `ats-check [--file <pdf>]` = parseability check; `templates` = list available LaTeX templates |
| `jobot coverletter <job-id|--url> [--tone --extra-prompt --output]` | Generate a profile-grounded cover letter for a job |
| `jobot qa [--job-id --question]` | Answer a job application question from the profile-grounded QA engine |
| `jobot apply --dry-run <job-id>` | One-shot tailored PDF + cover letter + ATS score, no submission |

> **Live browser submissions (Phase 5 — no fabrication)**: `naukri` and
> `linkedin` submissions require a real Patchright browser session. Without
> `JOBOT_RUN_LIVE_BROWSER=1` set, Naukri `submit/verify` return honest
> failures (pipeline marks the application FAILED) and LinkedIn raises
> `NotImplementedError` — jobot never invents confirmation IDs or fake
> submissions. With the env var set (and a logged-in session via
> `jobot login <portal>`), Naukri clicks the real Apply button and verifies
> against `mnjuser/myapplications`, and LinkedIn runs the Easy Apply saga
> with success-marker verification. Live opt-in tests:
> `JOBOT_RUN_LIVE_BROWSER=1 pytest tests/integration/test_naukri_live.py tests/integration/test_linkedin_easy_apply_live.py`.

> **PDF engines**: TeX renderer (`lualatex`) is used when installed (see
> Prerequisites §1); otherwise jobot falls back to a pure-Python reportlab
> renderer with identical output structure — no system TeX/poppler needed.
> `--engine latex|fallback` forces either. `jobot doctor` reports engine
> availability (informational, never fatal).

### Windows / PowerShell Encoding Note

Commands that render **rich tables** (`scrape`, `rank`, etc.) emit Unicode
box-drawing characters. PowerShell's default console code page (`cp1252`)
cannot encode these and `python` raises `UnicodeEncodeError` before the
command completes. Avoid this with any of:

- Use machine-readable output where supported (e.g. `jobot scrape ... --json`
  writes plain ASCII to stdout).
- Before running a rich command, set UTF-8 output and redirect to a file:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  python -m jobot.cli.main apply 1 --dry-run *> apply.log
  Get-Content apply.log -Encoding utf8
  ```
- Permanently (in your PowerShell profile):
  `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`.

### Interview Prep

| Command | Purpose |
|---|---|
| `jobot interview start [--track behavioral\|system_design\|technical]` | Start a multi-turn mock interview session |
| `jobot interview list` | List past interview sessions |
| `jobot interview answer --session <id> --answer "..."` | Submit an answer and get STAR coaching |
| `jobot interview review --session <id>` | Show per-question STAR scores |
| `jobot interview complete --session <id>` | Finish a session and show the average score |

### Career Analytics

| Command | Purpose |
|---|---|
| `jobot skill-gap [--limit N]` | Analyze skill demand from saved postings vs the profile; prints gap table + learning path recommendations |
| `jobot salary [--role <key> --region India\|US\|EU --roles]` | Look up a salary band (shipped YAML defaults; live benchmark opt-in via `JOBOT_RUN_LIVE_SALARY=1`) |

### Outreach

| Command | Purpose |
|---|---|
| `jobot outreach presets` | List available DM presets |
| `jobot outreach draft --preset <key> --name <first> --company <c> [--role <r> --output <file>]` | Draft a grounded DM (grounding gate enforced) + LinkedIn people-search URL |
| `jobot outreach send --preset <key> --name <first> --company <c> [--role <r>]` | Send the DM via SMTP (daily DM cap enforced; dry-run printout when SMTP unconfigured) |

### Scheduler & Loops

| Command | Purpose |
|---|---|
| `jobot loop scan-only` | Scrape + dedup + email summary, no apply |
| `jobot loop apply-only --max-apply N` | Apply to top N jobs from saved pool |
| `jobot loop digest --period weekly` | Send weekly/monthly digest email |
| `jobot loop full-loop --max-apply N` | Full daily loop: scrape + apply + digest |
| `jobot loop interview-prep <job-id>` | Run mock interview for upcoming interview |
| `jobot loop outreach-batch <preset> --count N` | Send N cold DMs to recruiters |

### Plugin Management

| Command | Purpose |
|---|---|
| `jobot plugin install <source>` | Install plugin from pip spec or git URL |
| `jobot plugin list` | List installed plugins |
| `jobot plugin audit` | Verify all installed plugins match audit hash |
| `jobot plugin remove <name>` | Uninstall a plugin |

### Maintenance & Backup

| Command | Purpose |
|---|---|
| `jobot backup` | Backup SQLite + blobs |
| `jobot restore <date>` | Restore from a backup |
| `jobot migrate` | Run pending schema migrations |
| `jobot migrate --rollback N` | Roll back N migrations |
| `jobot browser restore <board>` | Restore browser profile from backup |
| `jobot trace export <trace-id>` | Export a trace as OpenTelemetry JSON |
| `jobot quarantine list` | List quarantined (failed) tasks |
| `jobot quarantine replay <id>` | Replay a quarantined task |
| `jobot quarantine discard <id>` | Discard a quarantined task |

---

## 9. Troubleshooting & FAQ

### Browser launches but LinkedIn login fails

**Cause:** Patchright's persistent context lost the login session.

**Fix:** Open a visible browser, log in manually once:
```bash
jobot browser login --board linkedin --headed
```

### LLM API key works in curl but not in JoBot

**Cause:** Key is in `.env` (Tier 1) but JoBot reads from OS keyring (Tier 3).

**Fix:**
```bash
jobot config set llm.api_key.gemini AIza...
# Remove from .env
jobot config get llm.api_key.gemini  # verify
```

### SQLite database is locked

**Cause:** Concurrent writer contention.

**Fix:**
```bash
fuser ~/.jobot/data/jobot.db          # find the writer
kill -9 <pid>                          # if stale
sqlite3 ~/.jobot/data/jobot.db 'PRAGMA integrity_check;'
```

### LaTeX resume generation fails on missing font

**Cause:** TeX Live minimal install missing a required package.

**Fix:**
```bash
# macOS
brew install --cask mactex
# Linux
sudo apt install texlive-full
# Or use Tectonic (auto-downloads packages on demand):
brew install tectonic  # macOS
sudo snap install tectonic  # Linux
```

### Captcha solver returns garbage

**Cause:** 2captcha API key invalid OR captcha type unsupported.

**Fix:**
```bash
# Disable auto-captcha, fall back to human:
jobot config set captcha.solver human

# Or use LLM-assisted solver for text/math captchas:
jobot config set captcha.solver llm
```

### Apply saga left job in half-applied state

**Cause:** Saga crashed between steps.

**Fix:**
```bash
jobot apply --resume <saga-id>
# If checkpoint corrupt:
sqlite3 ~/.jobot/data/jobot.db 'SELECT * FROM applications WHERE id="abc123";'
jobot tracker move abc123 failed  # mark as unrecoverable
```

### OS keyring not available on WSL2

**Cause:** gnome-keyring daemon not running inside WSL2.

**Fix:**
```bash
eval $(gnome-keyring-daemon --start); export SSH_AUTH_SOCK
# Add to ~/.bashrc

# Or use encrypted-file fallback:
export JOBOT_KEYRING_BACKEND=file
export JOBOT_KEYRING_FILE=~/.jobot/keyring.enc
```

### JobSpy rate-limited by LinkedIn (HTTP 429)

**Cause:** LinkedIn detected the scraper pattern (per-IP rate limiting).

**Fix:**
```bash
# Reduce rate:
jobot config set scraper.jobspy.delay_s 5
# Enable proxy rotation (comma-separated list):
jobot config set scraper.jobspy.proxy_list "http://p1:8080,http://p2:8080"
# Or skip LinkedIn, use direct-API adapters (never rate-limited the same way):
jobot scrape lever --companies toptal
jobot scrape careers --companies webflow,figma,vercel,notion,benchling
```

### PII masker is over-aggressive

**Cause:** LLM-assisted masker flags common words as PII.

**Fix:**
```bash
jobot config set pii.masker regex-only  # disable LLM-assist
```

### Daily cap reached unexpectedly

**Cause:** Yesterday's batch ran past midnight UTC.

**Fix:** Either run daily loop earlier (8am UTC) or raise cap:
```bash
jobot config set policy.daily_apply_cap 100
```

### Resume LaTeX produces PDF but ATS check fails

**Cause:** Two-column template confuses pdftotext extraction.

**Fix:** Use single-column template:
```bash
jobot resume tailor --template default  # ATS-safe
# 'modern' (two-column) is for human review only
```

### Cover letter sounds like every other LLM cover letter

**Fix:**
```bash
# Lower temperature:
jobot coverletter generate --tone technical --extra-prompt 'Mention the candidate's experience with Paxos.'
```

### Browser profile corrupt after crash

**Fix:**
```bash
jobot browser restore linkedin
# If no backup:
rm -rf ~/.jobot/browser-profiles/linkedin/
jobot browser login --board linkedin --headed
```

### Docker container keeps restarting

**Cause:** Healthcheck fails because LLM provider unreachable (no API key set).

**Fix:**
```bash
docker compose run --rm jobot config set llm.api_key.gemini AIzaSy...
docker compose restart jobot
docker compose logs jobot | tail -50
```

### JobSpy returns 0 results for an obvious search

**Cause:** (1) the `python-jobspy` library is not installed (you'll see
`JobSpyNotInstalledError` — install via the `--no-deps` recipe above), (2) the
board is rate-limited, or (3) you used a board JobSpy can't serve well right
now.

**Fix:** Check the per-board message first:
```bash
jobot scrape linkedin --keywords 'engineer'   # lowercase site names
jobot scrape indeed --keywords 'engineer'     # alternative board
# Google board requires the google_search_term param (auto-set by --keywords);
# if it still returns 0, the upstream google scraper is flaky — use another board.
```

### JobBot is slow on first scrape

**Cause:** First-time scraping pulls many postings and the dedup cache is
empty.

**Fix:** This is expected; the local pseudo-embedding is fast (no LLM calls).
Warm the persistent dedup cache once:
```bash
jobot scrape --all --limit 50
jobot dedup --stats   # verify cache size
```

---

## Next Steps

1. **Read [PLAN.md](./PLAN.md)** for the full architecture and merge plan.
2. **Run `jobot doctor`** after install to verify environment.
3. **Start Phase 0** of the migration roadmap (audit + cleanup).
4. **Open issues** on the JoBot GitHub repo for any specific module you'd like to prioritize.
