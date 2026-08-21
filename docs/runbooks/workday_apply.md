# Operational Runbook: Workday Application Execution

> **Target Platform:** Workday Career Sites (`myworkdayjobs.com`)  
> **Adapter Class:** `WorkdayAdapter` (`src/jobot/adapters/workday.py`)  
> **Capability Tier:** Level 3 (CXS Feed Scraping + Stealth Browser Form Fill)  
> **Default Daily Cap:** 30 submissions / 24 hours  

---

## 1. Overview & Workday Architecture

Workday job portals expose JSON CXS feeds (`/wday/cxs/<tenant>/<site>/jobs`) for job discovery and requisition details. Application submission requires an authenticated applicant account and multi-page form navigation across standard Workday steps.

---

## 2. Scraping & Requisition Discovery

JoBot parses Workday job URLs directly or queries the tenant's public CXS feed:

```bash
# Parse and save a direct Workday requisition URL
jobot run --url "https://target.wd1.myworkdayjobs.com/Careers/job/Remote/Senior-Software-Engineer_R-12345" --dry-run
```

---

## 3. Application Execution Workflow

### Step 1: Candidate Account Credentials
Workday requires candidate accounts per employer tenant. Store credentials in the local vault:
```bash
jobot profile
```

### Step 2: Form Navigation & Autofill
When executed with `--approve` (and `JOBOT_RUN_LIVE_BROWSER=1`):
1. **Quick Apply / Create Account**: Browser navigates to the application entrypoint.
2. **Resume Ingestion**: Uploads candidate tailored PDF (`DocumentTailor` output). Workday parses experience blocks.
3. **Information Reconciliation**: Corrects parsed fields against `CandidateTruthStore` facts.
4. **Voluntary Disclosures**: Completes EEO, Veteran status, and Disability declarations based strictly on profile preferences.
5. **Review & Final Dispatch**: Clicks Submit on the final review page.
6. **Receipt Verification**: Verifies presence of the Workday submission confirmation card and captures PNG evidence.
