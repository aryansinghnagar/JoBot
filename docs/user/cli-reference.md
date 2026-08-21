# JoBot CLI Reference Guide

Comprehensive command-line interface specification for **JoBot** (v0.2.0) — the Local-First Autonomous Job Application Operating System.

```bash
jobot [OPTIONS] COMMAND [ARGS]...
```

---

## Command Categories

1. [Setup & System Configuration](#1-setup--system-configuration)
2. [Candidate Profile & Truth Ledger](#2-candidate-profile--truth-ledger)
3. [Discovery, Scraping & Site Health](#3-discovery-scraping--site-health)
4. [Application Pipeline & Execution](#4-application-pipeline--execution)
5. [Document Generation & ATS Scoring](#5-document-generation--ats-scoring)
6. [Career Intelligence & Analytics](#6-career-intelligence--analytics)
7. [Networking & Outreach](#7-networking--outreach)
8. [Daemon Loops & Background Scheduling](#8-daemon-loops--background-scheduling)
9. [Plugins & Extensibility](#9-plugins--extensibility)
10. [Observability, Diagnostics & Tracing](#10-observability-diagnostics--tracing)
11. [Data Export & Maintenance](#11-data-export--maintenance)

---

## 1. Setup & System Configuration

### `jobot setup`
Initialize local directories (`~/.jobot/`), database schemas, and cryptographic vault.
```bash
jobot setup
jobot setup --force
```
- `--profile-name TEXT`: Specify custom profile namespace (default: `default`).
- `--force`: Reinitialize database tables and configuration files without prompting.

### `jobot config`
Manage configuration values in `~/.jobot/config.yaml` and OS Keyring API keys.
```bash
# Display full configuration (secrets automatically masked)
jobot config show

# Get specific configuration value
jobot config get llm.provider

# Set configuration parameter
jobot config set llm.provider gemini
jobot config set llm.model gemini-2.5-flash

# Store secure API credentials in OS Keyring
jobot config set api_keys.gemini <YOUR_API_KEY>

# Remove configuration key
jobot config unset llm.temperature
```

### `jobot doctor`
Run deep environment diagnostics, checking Python 3.11+, SQLite WAL mode, Patchright binaries, Fernet vault integrity, OS keyring connectivity, and LLM provider credentials.
```bash
jobot doctor
```

### `jobot sidecar`
Launch high-speed stdio JSON-RPC 2.0 sidecar server for the Tauri 2 / React 19 desktop GUI.
```bash
jobot sidecar
```

---

## 2. Candidate Profile & Truth Ledger

### `jobot profile`
Display or initialize candidate identity facts and ground truth parameters.
```bash
# View active profile facts
jobot profile

# Interactively initialize candidate profile
jobot profile --init

# Specify custom profile namespace
jobot profile --name dev_profile
```

### `jobot import-resume`
Ingest existing resumes (PDF, Word `.docx`, or plain text) into the `CandidateTruthStore` and answer bank.
```bash
jobot import-resume path/to/resume.pdf
jobot import-resume path/to/resume.docx --name dev_profile
```

### `jobot qa`
Generate grounded answers to application form questions using profile facts with zero hallucination.
```bash
jobot qa --question "How many years of Python experience do you have?"
jobot qa --question "Describe your experience with Kubernetes." --job-id <JOB_ID>
```

---

## 3. Discovery, Scraping & Site Health

### `jobot list-sites`
List all supported ATS portals, scraper engines, and adapter capability tiers (Level 4 Direct API, Level 3 Stealth Browser, Level 2 Discovery-Only).
```bash
jobot list-sites
```

### `jobot site-health`
Check connectivity, HTTP latency, and circuit-breaker status across supported job portals.
```bash
# Inspect all registered portals
jobot site-health --all

# Check specific portal
jobot site-health --site greenhouse
jobot site-health --site linkedin
```

### `jobot scrape`
Discover matching job postings from ATS APIs and aggregated job feeds.
```bash
# Scrape public ATS board APIs (Zero browser overhead)
jobot scrape greenhouse --companies stripe,airbnb,cloudflare --save
jobot scrape lever --companies netflix,spotify --save
jobot scrape ashby --companies linear,notion --save

# Scrape aggregated job feeds (JobSpy engine)
jobot scrape linkedin --keywords "Senior Backend Engineer" --location "Remote" --limit 50 --save
jobot scrape indeed --keywords "Python Distributed Systems" --location "San Francisco, CA" --limit 25 --save
jobot scrape naukri --keywords "Staff Software Engineer" --location "Bengaluru" --limit 20 --save
```
- `--keywords TEXT`: Keyword search filter.
- `--location TEXT`: Geographic location or "Remote".
- `--limit INTEGER`: Maximum postings to fetch (default: 25).
- `--companies TEXT`: Comma-separated company slugs (for ATS scrapers).
- `--save`: Persist fetched postings to SQLite database for matching and application.

### `jobot dedup`
Inspect or reset deduplication cache and duplicate posting statistics.
```bash
# Show deduplication index metrics
jobot dedup --stats

# Purge deduplication cache
jobot dedup --clear
```

### `jobot login`
Interactively log into target portals via Patchright browser automation and persist session cookies.
```bash
# Interactive login with automatic OTP pause
jobot login naukri

# Check active stored session directories
jobot login --status

# Clear cookies and stored session for portal
jobot login --logout naukri
```

---

## 4. Application Pipeline & Execution

### `jobot apply`
Execute the 12-Phase Application Submission Pipeline (ASP) for a target job posting ID or direct URL.
```bash
# Supervised apply with human approval gate (Phase 10)
jobot apply <JOB_ID>

# Apply directly via job posting URL
jobot apply --url "https://boards.greenhouse.io/stripe/jobs/12345"

# Auto-approve submission (autonomous mode)
jobot apply <JOB_ID> --approve

# Dry-run execution without network side-effects
jobot apply <JOB_ID> --dry-run
```

### `jobot run`
Execute the 12-Phase ASP for a single target URL with automatic portal inference.
```bash
jobot run --url "https://jobs.lever.co/spotify/67890" --approve
```

### `jobot auto-apply`
Run batch matching and application across saved database postings filtered by matching threshold.
```bash
# Supervised dry-run review of candidate matches
jobot auto-apply --min-match 0.80 --dry-run

# Run auto-apply across specific portal
jobot auto-apply --site greenhouse --min-match 0.85 --limit 10
```
- `--site TEXT`: Target portal adapter name.
- `--min-match FLOAT`: Minimum match score threshold between 0.0 and 1.0 (default: 0.75).
- `--limit INTEGER`: Maximum applications to process in batch.
- `--dry-run`: Evaluate matching ladder and phase 1–9 without submitting.
- `--auto-submit`: Grant autonomous submission clearance.

### `jobot continuous-campaign`
Launch round-robin continuous application campaign across active portals with daily policy cap enforcement and evidence logging.
```bash
# Supervised campaign execution
jobot continuous-campaign --portals greenhouse,lever,workday

# High-throughput campaign with custom daily limit
jobot continuous-campaign --max-daily-apps 25 --interval 10
```
- `--portals TEXT`: Comma-separated list of active portals.
- `--max-daily-apps INTEGER`: Hard daily cap on submissions (default: 50).
- `--interval INTEGER`: Seconds between campaign execution passes (default: 5).
- `--auto-submit`: Enable fully autonomous submission (requires user confirmation).
- `--dry-run`: Execute full discovery, matching, and form filling without final submission.

### `jobot status`
Display live runner status, active task leases, and campaign progress.
```bash
jobot status
```

### `jobot pause` / `jobot resume`
Pause and resume active automation runners and continuous campaigns.
```bash
jobot pause
jobot resume
```

---

## 5. Document Generation & ATS Scoring

### `jobot coverletter`
Generate a grounding-verified, tailored cover letter for a target job description.
```bash
jobot coverletter --job-id <JOB_ID> --output cover_letter.pdf
jobot coverletter --url "https://boards.greenhouse.io/stripe/jobs/12345" --tone professional
```
- `--job-id TEXT`: ID of saved job posting.
- `--url TEXT`: Direct URL to job posting.
- `--template TEXT`: Template style (`classic`, `modern`, `minimal`).
- `--tone TEXT`: Tone selection (`professional`, `enthusiastic`, `concise`, `technical`).
- `--output PATH`: File destination for generated cover letter.

---

## 6. Career Intelligence & Analytics

### `jobot interview`
Interactive AI interview preparation coach with domain-specific question banks and rubric scoring.
```bash
# Practice technical system design interview
jobot interview --topic "system_design" --difficulty "senior"

# Practice behavioral STAR method interview
jobot interview --topic "behavioral" --mock

# Review past interview session analysis
jobot interview --analyze
```

### `jobot skill-gap`
Analyze candidate resume against job requisitions to identify missing keywords, certifications, and experience gaps.
```bash
jobot skill-gap --job-id <JOB_ID>
jobot skill-gap --url "https://jobs.lever.co/netflix/123"
```

### `jobot salary`
Benchmark compensation bands using title, location, and seniority datasets.
```bash
jobot salary --title "Staff Backend Engineer" --location "San Francisco, CA"
jobot salary --title "Lead Python Developer" --location "Remote" --experience 8
```

### `jobot tracker`
Render interactive HTML job application tracker and metrics dashboard.
```bash
# Render dashboard and open in default web browser
jobot tracker --dashboard

# Export standalone HTML dashboard
jobot tracker --render-html --output ~/Desktop/job_tracker.html
```

### `jobot digest`
Generate and dispatch daily summary digest of scraped opportunities and application statuses.
```bash
# Print summary digest to terminal
jobot digest --generate

# Send formatted digest email via configured SMTP
jobot digest --send --email user@example.com
```

---

## 7. Networking & Outreach

### `jobot outreach`
Generate personalized LinkedIn InMail, connection request, or recruiter outreach email drafts.
```bash
jobot outreach --company "Stripe" --role "Staff Infrastructure Engineer" --channel "linkedin"
jobot outreach --company "Netflix" --recruiter "Jane Doe" --role "Senior Platform Engineer" --channel "email"
```
- `--company TEXT`: Target employer name.
- `--role TEXT`: Target requisition title.
- `--recruiter TEXT`: Recruiter or hiring manager name.
- `--channel TEXT`: Communication channel (`linkedin`, `email`, `twitter`).

---

## 8. Daemon Loops & Background Scheduling

### `jobot schedule`
Manage cron-style background jobs for automated scraping and campaigns.
```bash
# List active background schedules
jobot schedule list

# Add recurring schedule (every weekday at 9:00 AM)
jobot schedule add --cron "0 9 * * 1-5" --command "continuous-campaign"

# Remove schedule by ID
jobot schedule remove --id <SCHEDULE_ID>
```

### `jobot loop`
Run persistent polling daemon loop for job discovery and auto-application.
```bash
jobot loop --interval 3600
jobot loop --interval 1800 --max-iterations 10
```

---

## 9. Plugins & Extensibility

### `jobot plugin`
Manage third-party site adapters and extensions under deny-by-default security policies.
```bash
# List installed plugins
jobot plugin list

# Install plugin from approved git repository
jobot plugin install https://github.com/example/jobot-custom-ats.git

# Security audit installed plugin AST and network calls
jobot plugin audit custom-ats

# Uninstall plugin
jobot plugin uninstall custom-ats
```

---

## 10. Observability, Diagnostics & Tracing

### `jobot traces`
Inspect OpenTelemetry-compatible execution spans and pipeline telemetry.
```bash
# List recent execution traces
jobot traces list

# Show detailed phase timeline for specific application run
jobot traces show <RUN_ID>
```

### `jobot alerts`
View operational notifications (tripped circuit breakers, daily caps reached, authentication drops).
```bash
# View all alerts
jobot alerts --all

# Acknowledge operational alert by ID
jobot alerts --ack <ALERT_ID>
```

### `jobot evals`
Execute automated benchmark evaluation suites across grounding, safety, daily cap, and circuit breaker categories.
```bash
jobot evals
jobot evals --category grounding
jobot evals --suite circuit_breaker_check --report
```

### `jobot report-issue`
Generate a structured diagnostic bug bundle with system logs, sanitized configuration, and OS environment data.
```bash
jobot report-issue --title "Greenhouse form submit error"
```

### `jobot test-logs`
Tail or clear local execution and diagnostic logs (`~/.jobot/logs/`).
```bash
jobot test-logs --tail 50
jobot test-logs --clear
```

---

## 11. Data Export & Maintenance

### `jobot export`
Export complete application history, evidence logs, and status records.
```bash
jobot export --format csv --output ~/Desktop/applications.csv
jobot export --format json --output ~/Desktop/applications.json
```

### `jobot reset-db`
Reset the local SQLite control plane database and rebuild tables from current schema migrations.
```bash
jobot reset-db --force
```

---

## Environment Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `JOBOT_DB_PATH` | Path | `~/.jobot/jobot.db` | SQLite database file location |
| `JOBOT_CONFIG_PATH` | Path | `~/.jobot/config.yaml` | YAML configuration file location |
| `JOBOT_PROFILE_PATH` | Path | `~/.jobot/vault.enc` | Fernet-encrypted candidate profile vault |
| `JOBOT_EVIDENCE_DIR` | Path | `~/.jobot/evidence/` | Local directory for screenshots and DOM snapshots |
| `JOBOT_LOG_LEVEL` | String | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `JOBOT_RUN_LIVE_BROWSER` | Flag (`0`/`1`) | `0` | Enable real headless/headful browser automation |
| `JOBOT_RUN_LIVE_LLM` | Flag (`0`/`1`) | `0` | Enable real LLM API calls in test runners |
| `JOBOT_RUN_LIVE_SCRAPE` | Flag (`0`/`1`) | `0` | Enable live external network scraping in test runners |

