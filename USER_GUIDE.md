# JoBot — End-to-End User Guide & Operational Manual

Welcome to the **JoBot User Guide**. This document covers every feature, workflow, and command in JoBot, from initial profile setup to autonomous high-throughput campaign execution and human-governed approvals.

---

## Table of Contents
1. [Core Philosophy & Architecture](#1-core-philosophy--architecture)
2. [Candidate Profile & Ground Truth Management](#2-candidate-profile--ground-truth-management)
3. [Job Discovery & Multi-Board Scraping](#3-job-discovery--multi-board-scraping)
4. [4-Stage Matching Ladder](#4-4-stage-matching-ladder)
5. [Grounding-Verified Document Tailoring](#5-grounding-verified-document-tailoring)
6. [Application Submission Pipeline](#6-application-submission-pipeline)
7. [Human-in-the-Loop Approval Governance](#7-human-in-the-loop-approval-governance)
8. [Evidence Protocol & Non-Repudiation](#8-evidence-protocol--non-repudiation)
9. [Campaign Mode & Automated Scheduling](#9-campaign-mode--automated-scheduling)
10. [Site Health & Circuit Breakers](#10-site-health--circuit-breakers)
11. [Desktop GUI Cockpit Walkthrough](#11-desktop-gui-cockpit-walkthrough)
12. [Disaster Recovery, Backups & Maintenance](#12-disaster-recovery-backups--maintenance)

---

## 1. Core Philosophy & Architecture

JoBot is built upon three foundational tenets:
1. **Candidate Grounding Verification**: AI generation is anchored to an immutable fact store (`CandidateTruthStore`). Profile facts are verified using heuristic token overlap and entity checks to prevent ungrounded claims.
2. **Reconcile-Never-Replay**: Network side-effects are tracked in an append-only effect ledger (`external_effects`). Ambiguous network drops transition into a `SUBMISSION_UNKNOWN` state resolved only via read-only confirmation polling—never double-submitted.
3. **Local-First Cryptographic Security**: All credentials, resumes, and personal facts reside encrypted in your local OS storage (`~/.jobot/vault.enc`) under strict `0600` permissions.

---

## 2. Candidate Profile & Ground Truth Management

### Initializing Your Encrypted Profile
```bash
jobot profile init
```
This command initializes your candidate profile vault. You will be prompted for:
- Full Name, Primary Email, Phone Number, Location
- Work Authorization Status (US Citizen, Green Card, H-1B, etc.)
- Target Roles, Minimum Acceptable Salary, Preferred Locations

### Seeding Truth Facts via Resume Ingestion
JoBot can parse PDF or text resumes and populate your candidate ground truth ledger automatically:
```bash
jobot import-resume ~/Documents/Resume.pdf
```
This extracts:
- Educational credentials (Institutions, Degrees, GPAs, Graduation Years)
- Employment history (Companies, Job Titles, Start/End Dates)
- Quantified accomplishments and metrics
- Core skills and technical certifications

### Inspecting Profile & Answer Bank
```bash
# View active profile
jobot profile

# Test QA engine answer generation
jobot qa --question "How many years of Python experience do you have?"
```

---

## 3. Job Discovery & Multi-Board Scraping

JoBot supports discovery across direct ATS APIs (zero browser overhead) and aggregated job boards.

### Direct ATS Scraping
Query company career portals directly via public JSON endpoints:
```bash
# Scrape Greenhouse boards for specific companies
jobot scrape greenhouse --companies stripe,airbnb,figma --save

# Scrape Lever postings
jobot scrape lever --companies netflix,spotify --save

# Scrape Ashby, Workable, or BambooHR
jobot scrape ashby --companies linear,notion --save
jobot scrape workable --companies acme-corp --save
```

### Aggregated Job Board Scraping (JobSpy Engine)
Search aggregated job feeds with deduplication:
```bash
# Search LinkedIn, Indeed, Glassdoor, and ZipRecruiter simultaneously
jobot scrape linkedin --keywords "Senior Backend Engineer" --location "Remote" --limit 50 --save
jobot scrape indeed --keywords "Python Distributed Systems" --location "San Francisco, CA" --limit 25 --save
```

### Deduplication & Caching
JoBot compares incoming postings against stored jobs using composite hashing (Normalized Company + Title + Location) and cosine text similarity:
```bash
# Check deduplication stats
jobot dedup --stats
```

---

## 4. 4-Stage Matching Ladder

Rather than wasting LLM tokens on every posting, JoBot evaluates jobs through a **4-Stage Matching Ladder**:

```
[Stage 1: Hard Filter] (Location, Work Auth, Min Salary)
       │  (Passes)
       ▼
[Stage 2: Skill Overlap] (Jaccard Index ≥ 0.40)
       │  (Passes)
       ▼
[Stage 3: Vector Cosine Similarity] (Bigram Embedding ≥ 0.65)
       │  (Passes)
       ▼
[Stage 4: LLM Fit Reasoning] (Structured Pros/Cons Analysis & Score ≥ 80%)
```

### Running Batch Matching & Application
```bash
# Run auto-apply batch pipeline with filtering
jobot auto-apply --min-match 0.80 --dry-run
```

---

## 5. Grounding-Verified Document Tailoring

JoBot customizes resumes and cover letters using a **Two-Pass Drafter-Reviewer Loop**:
1. **Drafter Pass**: Generates tailored bullet points emphasizing relevant experiences matching the job description.
2. **Reviewer Pass**: Evaluates the drafted document against a 5-dimension rubric (Relevance, Impact, Conciseness, ATS Formatting, Grounding).
3. **Grounding Verification Gate**: Checks all extracted claims against `CandidateTruthStore`. Any unsupported claims trigger automatic revision loops.

### Tailoring Documents
```bash
# Dry run application (tailors resume, checks ATS score, drafts cover letter)
jobot apply <JOB_ID> --dry-run

# Generate a tailored cover letter (Tones: professional, conversational, confident, technical)
jobot coverletter <JOB_ID> --tone professional
```

---

## 6. Application Submission Pipeline

Applications follow a deterministic **12-Phase Application Submission Pipeline (ASP)**:

1. **Pre-flight Check**: Validates network connectivity and portal availability.
2. **Rate Limit & Policy Gate**: Checks daily portal quotas.
3. **Job Fetch & Parse**: Retrieves live form requirements.
4. **Candidate Grounding Verification**: Verifies profile coverage.
5. **Document Tailoring**: Drafts resume and cover letter.
6. **Artifact Compilation**: Builds vector PDF resume.
7. **Form Field Mapping**: Resolves form fields from profile and answer bank.
8. **Field Answer Generation**: Generates truthful custom responses.
9. **Payload Construction**: Prepares submission payload.
10. **Human Approval Gate**: Holds execution if `--approve` is specified.
11. **Idempotent Effect Reservation**: Registers reservation in `external_effects` table.
12. **Dispatch, Evidence Capture & Verification**: Submits form, records SHA256 DOM proof, and confirms submission ID.

### Platform Support Matrix & Submission Tiers

| Platform | Mode | Submission Method | Notes |
|---|---|---|---|
| **Greenhouse** | Real API | Direct HTTP POST | Server-confirmed application ID |
| **Lever** | Real API | Direct HTTP POST | Server-confirmed application ID |
| **Workday** | Browser | Patchright Browser Automation | Requires `JOBOT_RUN_LIVE_BROWSER=1` |
| **LinkedIn Easy Apply** | Browser | EasyApplySaga / Patchright | Requires `JOBOT_RUN_LIVE_BROWSER=1` |
| **Naukri** | Browser | Patchright Browser Automation | Requires `JOBOT_RUN_LIVE_BROWSER=1` |
| **Ashby, Workable, BambooHR, etc.** | Discovery Only | Not Supported | Raises `AdapterCapabilityError` on apply |
| **Indeed, Glassdoor, ZipRecruiter** | Discovery Only | Not Supported | Raises `AdapterCapabilityError` on apply |

### Applying to a Job
```bash
# Dry run: compiles documents and prepares form answers without submitting
jobot apply <JOB_ID> --dry-run

# Supervised apply: pauses at Phase 10 for human approval
jobot apply <JOB_ID> --approve

# Autonomous apply (for direct-API portals like Greenhouse / Lever)
jobot apply <JOB_ID>
```

---

## 7. Human-in-the-Loop Approval Governance

When running with `--approve` (or in supervised campaign mode), applications enter a pending state in SQLite (`approval_requests`).

### Reviewing & Approving via CLI
```bash
# Supervised application run awaiting interactive human approval
jobot apply <JOB_ID> --approve

# Single-run execution with approval prompt
jobot run --url "https://jobs.lever.co/example/12345" --approve
```

---

## 8. Evidence Protocol & Non-Repudiation

For every submitted application, JoBot generates a permanent, non-repudiation audit package under `.jobot/evidence/<APPLICATION_ID>/`:
- `pre_submission.html`: Pre-submit DOM snapshot.
- `post_submission.html`: Post-submit confirmation DOM snapshot.
- `confirmation.png`: Full-page confirmation screenshot.
- `manifest.json`: Contains timestamps, external confirmation IDs, and SHA256 cryptographic hashes of all snapshot files.

### Inspecting Traces & Status
```bash
# Inspect pipeline status
jobot status

# Inspect execution traces
jobot traces list
```

---

## 9. Campaign Mode & Automated Scheduling

Campaign mode runs continuous discovery, matching, and submission loops within user-defined rate limits and daily safety caps.

```bash
# Run continuous campaign loop
jobot continuous-campaign --portals greenhouse,lever,workday --max-daily-apps 25

# Pause and resume active campaign
jobot pause
jobot resume

# Configure scheduled cron automation
jobot schedule list
jobot schedule add --cron "0 9 * * 1-5" --command "continuous-campaign"
```

---

## 10. Career Intelligence & Outreach Tools

JoBot includes powerful analytical and communication tools to accelerate your search:

### AI Interview Preparation Coach
```bash
# Practice technical system design interview
jobot interview --topic "system_design" --difficulty "senior"

# Practice behavioral STAR method interview
jobot interview --topic "behavioral" --mock
```

### Skill Gap Analysis & Compensation Benchmarking
```bash
# Identify missing keywords and skills against a target requisition
jobot skill-gap --job-id <JOB_ID>

# Benchmark market salary bands
jobot salary --title "Staff Backend Engineer" --location "San Francisco, CA"
```

### Recruiter Outreach Generator & Daily Digest
```bash
# Generate personalized LinkedIn InMail outreach draft
jobot outreach --company "Stripe" --role "Staff Infrastructure Engineer" --channel "linkedin"

# Generate and email daily job search digest
jobot digest --generate
```

---

## 11. Site Health & Circuit Breakers

JoBot continuously tracks the availability, latency, and error rates of each job portal. If a portal experiences repeated failures or Cloudflare blocks, its circuit breaker trips to `OPEN`, temporarily pausing submissions to that portal while allowing other portals to continue.

```bash
# View live site health and circuit breaker states
jobot site-health --all

# Check adapter registry and capability flags
jobot list-sites

# Inspect operational alerts
jobot alerts --all
```

---

## 12. Desktop GUI Cockpit Walkthrough

JoBot includes a modern, high-speed native desktop cockpit powered by Tauri 2 and React 19.

### Launching the Desktop Cockpit
```bash
npm run tauri dev
```
*(Or launch the standalone installer executable `JoBot.exe` / `JoBot.dmg`)*

### Core Desktop Views & Features:
1. **Guided Onboarding Wizard (`Onboarding.jsx`)**:
   - **Drag-and-Drop Dropzone**: Ingests `.pdf`, `.docx`, and `.txt` resumes directly.
   - **Visual Fact Verification**: Instant badge chips showing extracted skills, contact info, and roles.
   - **AI Provider Cards**: 1-click setup for Google Gemini (Free Tier), Anthropic Claude, OpenAI, and Local Ollama with live connection testing.

2. **Application Cockpit & Kanban Board (`Dashboard.jsx`)**:
   - **5-Column Kanban Pipeline**: Visual swimlanes (`Discovered` ➔ `In Review` ➔ `Applied` ➔ `Interviewing` ➔ `Offered 🎉`).
   - **Productivity Metrics**: Real-time tracker calculating total applications and estimated **Time Saved (Hours)**.
   - **Table / Kanban Toggle**: Switch between visual cards and detailed tabular views.

3. **Job Discovery & ATS Badging (`Discover.jsx`)**:
   - **Transparent Capability Badging**: Distinguishes `[⚡ 1-Click Auto-Apply]` (Greenhouse, Lever, Workday, LinkedIn, Naukri) from `[🔗 Assisted Apply]` (Ashby, BambooHR, Indeed, Workable).
   - Real-time search by keyword, role, location, or target company.

4. **1-Click Apply & Assisted Mode (`Apply.jsx`)**:
   - **Supervised Co-Pilot**: Watch the bot safely fill forms with stealth browser physics.
   - **Assisted Apply Mode**: Automatically tailors the resume, copies the cover letter to clipboard, and launches the employer's portal in 1-click.
   - **1-Click Artifact Launching**: Open generated PDF resumes and cover letters in your OS default viewer with a single click.

5. **Approvals Inbox & Zero-Fabrication Governance (`Approvals.jsx`)**:
   - Card-by-card human review showing tailored cover letters, matched scores, and attached resumes before granting submission permission.
   - **Clipboard & File Helpers**: 1-click copy for tailored text and 1-click PDF preview.

6. **Candidate Truth Ledger (`Profile.jsx`)**:
   - Manage your locally encrypted ground truth facts, certified skills, and custom Q&A answers.
   - Drag-and-drop resume sync dropzone to refresh facts at any time.

7. **Site Health & Browser Engine Provisioning (`Health.jsx`)**:
   - Real-time health metrics, success rates, latency, and circuit breaker status.
   - **⚡ 1-Click Browser Engine Installer**: Download and verify stealth Chromium binaries with zero CLI commands.

8. **Campaign Controls & Settings (`Controls.jsx` & `Settings.jsx`)**:
   - Visual schedule presets (e.g. *Weekdays at 9:00 AM*, *Every 2 hours*) with 1-click Pause/Resume.
   - Live AI provider configuration, API key testing, and diagnostic data export.

---

## 13. Disaster Recovery, Backups & Maintenance

### Database Management & Health Checks
```bash
# Run comprehensive diagnostic doctor checks
jobot doctor

# Reset database schema and migrations if needed
jobot reset-db --force
```
