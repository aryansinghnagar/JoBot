# JoBot — Comprehensive Setup & Installation Guide

This guide covers installing, configuring, and verifying **JoBot** across **macOS**, **Linux**, and **Windows**.

---

## 1. System Requirements & Prerequisites

| Component | Minimum Requirement | Recommended | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11.0+` | `3.12+` or `3.14` | Core engine, orchestrator, scrapers, AI pipeline |
| **Node.js** | `20.19.0+` | `22.x LTS` | Desktop GUI frontend (Vite + React) |
| **Rust / Cargo** | `1.75.0+` | `1.85+` | Desktop GUI native shell (Tauri 2) *(GUI build only)* |
| **OS Keyring** | Secret Service / Keychain / DPAPI | System default | Secure vault encryption key storage |
| **SQLite** | `3.35.0+` (built-in Python) | `3.40+` | WAL-mode control plane and task database |

---

## 2. Step-by-Step Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/aryansinghnagar/JoBot.git
cd JoBot
```

### Step 2: Set Up Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on Linux / macOS
source .venv/bin/activate

# Activate on Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Core & Scraper Dependencies
```bash
# Install package in editable mode with dev and scraper dependencies
pip install --upgrade pip
pip install -e ".[dev,scrapers]"
```

### Step 4: Install Stealth Browser Automation Engine
JoBot uses `Patchright` (an anti-detection stealth fork of Playwright):
```bash
patchright install chromium
```

---

## 3. Profile & Credential Vault Setup

JoBot uses an encrypted, local-first candidate vault (`~/.jobot/vault.enc`) locked with symmetric Fernet encryption (`AES-128-CBC` + `HMAC-SHA256`) and file permissions strictly set to `0600`.

### Step 1: Initialize Candidate Profile
```bash
jobot profile init
```
This prompts for your basic candidate information (Name, Email, Phone, Location, Work Authorization) and securely creates your vault.

### Step 2: Seed Candidate Truth Facts (Resume Ingestion)
To enable the zero-hallucination grounding verifier, import your resume (PDF or plain text):
```bash
jobot import-resume path/to/your/resume.pdf
```
This automatically parses your work experience, education, skills, and certifications directly into the `CandidateTruthStore` and `answer_bank`.

### Step 3: Verify Profile & Truth Ledger
```bash
# View active profile summary
jobot profile show

# View immutable candidate facts
jobot truth facts
```

---

## 4. LLM Provider Configuration

JoBot includes a provider-neutral `ModelRouter` supporting 8 backends:

```bash
# Choose your preferred provider (gemini, openai, anthropic, mistral, cohere, ollama)
jobot config set llm.provider gemini

# Set your API Key (stored securely in OS keyring)
jobot config set api_keys.gemini <YOUR_GEMINI_API_KEY>
```

### Provider Configuration Matrix

| Provider | Provider ID | Config API Key Key | Default Model | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Google Gemini** *(Recommended)* | `gemini` | `api_keys.gemini` | `gemini-2.5-flash` | High token speed, native async streaming |
| **Anthropic Claude** | `anthropic` | `api_keys.anthropic` | `claude-3-5-sonnet-20241022` | Advanced reasoning for resume tailoring |
| **OpenAI** | `openai` | `api_keys.openai` | `gpt-4o` | Structured JSON output |
| **Mistral AI** | `mistral` | `api_keys.mistral` | `mistral-large-latest` | Fast European cloud provider |
| **Cohere** | `cohere` | `api_keys.cohere` | `command-r-plus` | Strong extraction capabilities |
| **Ollama (Local)** | `ollama` | *(None needed)* | `llama3.3:70b` | 100% offline & local execution |
| **AWS Bedrock** | `bedrock` | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | `anthropic.claude-3-5-sonnet` | Uses standard AWS SDK / IAM credentials |
| **GCP Vertex AI** | `vertex` | `GOOGLE_APPLICATION_CREDENTIALS` | `gemini-1.5-pro` | Uses GCP service account credentials |

To run completely offline with Ollama:
```bash
ollama run llama3.3:70b
jobot config set llm.provider ollama
jobot config set llm.model llama3.3:70b
jobot config set llm.ollama_endpoint http://localhost:11434
```

---

## 5. Desktop GUI Setup (Tauri 2 + React)

JoBot includes a native desktop cockpit providing human approval inboxes, live site health monitoring, and visual evidence inspection.

### Step 1: Install Frontend Dependencies
```bash
npm install
```

### Step 2: Run GUI in Development Mode
```bash
npm run tauri dev
```

### Step 3: Build Standalone Desktop Binary
```bash
npm run tauri build
```
The compiled installer / binary will be generated under `gui/src-tauri/target/release/bundle/`.

---

## 6. Environment Variables Reference

While `jobot config` stores settings in `~/.jobot/config.yaml` and credentials in the OS keyring, environment variables take precedence:

| Environment Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `JOBOT_DB_PATH` | Path | `~/.jobot/jobot.db` | Path to SQLite database |
| `JOBOT_CONFIG_PATH` | Path | `~/.jobot/config.yaml` | Path to configuration YAML |
| `JOBOT_PROFILE_PATH` | Path | `~/.jobot/profile.enc` | Path to encrypted candidate profile vault |
| `JOBOT_EVIDENCE_DIR` | Path | `~/.jobot/evidence/` | Directory where DOM snapshots & screenshots are saved |
| `JOBOT_LOG_LEVEL` | String | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `JOBOT_RUN_LIVE_BROWSER` | Boolean (`0`/`1`) | `0` | Enable live browser launches (required for Easy Apply sagas) |
| `JOBOT_RUN_LIVE_LLM` | Boolean (`0`/`1`) | `0` | Enable real external LLM API calls in test runners |
| `JOBOT_RUN_LIVE_SCRAPE` | Boolean (`0`/`1`) | `0` | Enable live external network scraping in test runners |

---

## 7. System Diagnostics & Health Check

Run the built-in diagnostic tool to verify database integrity, keyring connectivity, browser drivers, and LLM endpoints:

```bash
jobot doctor
```

Example healthy output:
```
[PASS] Python Version: 3.14.6
[PASS] Database: Connected (SQLite WAL mode, schema version 3)
[PASS] Vault: Initialized (~/.jobot/vault.enc, 0600 perms)
[PASS] Keyring: Available (SecretService/DPAPI/Keychain)
[PASS] Browser: Patchright Chromium available
[PASS] LLM Router: Gemini provider reachable (latency: 184ms)
[PASS] Storage: Hot backup capability verified
```

---

## 8. Database Management & Disaster Recovery

### Run Migrations
```bash
jobot db migrate
```

### Create Atomic Hot Backup
```bash
jobot db backup --out ~/.jobot/backups/jobot_backup_$(date +%Y%m%d).db
```

### Restore Database
```bash
jobot db restore ~/.jobot/backups/jobot_backup_20260816.db
```

---

## 9. Troubleshooting & FAQ

### Q: Keyring fails on headless Linux servers
On headless Linux servers without a desktop keyring daemon, configure the Python keyring backend to use `keyrings.alt.file.EncryptedKeyring` or export `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` and rely on environment variables.

### Q: Patchright browser fails to launch
Ensure required system browser dependencies are installed:
```bash
patchright install-deps chromium
```

### Q: Captcha encountered during browser automation
JoBot flags captchas and triggers a human notification. In desktop GUI mode, you can resolve the captcha interactively in the visible browser window before JoBot resumes automated submission.
