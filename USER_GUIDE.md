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
jobot import-resume ~/Documents/Aryan_Resume.pdf
```
This extracts:
- Educational credentials (Institutions, Degrees, GPAs, Graduation Years)
- Employment history (Companies, Job Titles, Start/End Dates)
- Quantified accomplishments and metrics
- Core skills and technical certifications

### Inspecting Profile & Answer Bank
```bash
# View active profile
jobot profile show

# View immutable candidate facts
jobot truth facts

# Search learned form field answers
jobot answer-bank search "years of python experience"
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

### Running the Matching Ladder
```bash
# Evaluate all newly scraped jobs
jobot match-jobs

# Filter by minimum match score
jobot match-jobs --min-score 85 --json
```

---

## 5. Grounding-Verified Document Tailoring

JoBot customizes resumes and cover letters using a **Two-Pass Drafter-Reviewer Loop**:
1. **Drafter Pass**: Generates tailored bullet points emphasizing relevant experiences matching the job description.
2. **Reviewer Pass**: Evaluates the drafted document against a 5-dimension rubric (Relevance, Impact, Conciseness, ATS Formatting, Grounding).
3. **Grounding Verification Gate**: Checks all extracted claims against `CandidateTruthStore`. Any unsupported claims trigger automatic revision loops.

### Tailoring Documents
```bash
# Tailor resume for a specific job
jobot resume tailor <JOB_ID> --template modern --engine reportlab

# Generate a tailored cover letter (Tones: professional, conversational, confident, technical)
jobot coverletter generate <JOB_ID> --tone professional

# Check ATS compatibility score (requires ≥ 0.85 to pass)
jobot resume ats-check <JOB_ID>
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
# List all pending approval requests
jobot approvals list

# Inspect detailed draft values for an application
jobot approvals inspect <REQUEST_ID>

# Approve and dispatch submission
jobot approvals decide <REQUEST_ID> --approve

# Reject application
jobot approvals decide <REQUEST_ID> --deny --reason "Not interested in hybrid model"
```

---

## 8. Evidence Protocol & Non-Repudiation

For every submitted application, JoBot generates a permanent, non-repudiation audit package under `.jobot/evidence/<APPLICATION_ID>/`:
- `pre_submission.html`: Pre-submit DOM snapshot.
- `post_submission.html`: Post-submit confirmation DOM snapshot.
- `confirmation.png`: Full-page confirmation screenshot.
- `manifest.json`: Contains timestamps, external confirmation IDs, and SHA256 cryptographic hashes of all snapshot files.

### Inspecting Evidence
```bash
jobot evidence show <APPLICATION_ID>
```

---

## 9. Campaign Mode & Automated Scheduling

Campaign mode runs continuous discovery, matching, and submission loops within user-defined rate limits and daily safety caps.

```bash
# Run campaign mode with a maximum of 20 applications per day
jobot campaign run --daily-cap 20 --interval-min 45 --supervised

# View active campaign statistics
jobot campaign stats
```

---

## 10. Site Health & Circuit Breakers

JoBot continuously tracks the availability, latency, and error rates of each job portal. If a portal experiences repeated failures or Cloudflare blocks, its circuit breaker trips to `TRIPPED`, temporarily pausing submissions to that portal while allowing other portals to continue.

```bash
# View live site health dashboard
jobot site-health

# Reset a tripped circuit breaker
jobot site-health reset greenhouse
```

---

## 11. Desktop GUI Cockpit Walkthrough

Launch the desktop cockpit:
```bash
npm run tauri dev
```

### GUI Views:
- **Dashboard**: High-level metrics, active applications count, success rates, and campaign status.
- **Approvals Inbox (`Approvals.jsx`)**: Card-by-card human review interface showing match scores, tailored cover letters, and one-click *Approve & Submit* buttons.
- **Discover**: Visual job feed search with live filters and matching ladder badges.
- **Site Health (`Health.jsx`)**: Real-time status table showing portal latency, success rates, and circuit state.
- **Settings**: LLM provider switching, rate limit adjustments, and vault management.

---

## 12. Disaster Recovery, Backups & Maintenance

### Hot Backups (Zero-Downtime SQLite Backup)
```bash
# Create immediate hot backup
jobot db backup --out ~/.jobot/backups/backup_$(date +%Y%m%d).db

# Restore from a backup file
jobot db restore ~/.jobot/backups/backup_20260816.db
```

### System Cleanup & Compaction
```bash
# Vacuum and optimize SQLite database indexes
jobot db optimize

# Clean up stale screenshot artifacts older than 90 days
jobot clean --older-than 90d
```
