# Operational Runbook: Naukri Application Execution

> **Target Platform:** `naukri.com`  
> **Adapter Class:** `NaukriAdapter` (`src/jobot/adapters/naukri/`)  
> **Capability Tier:** Level 3 (Stealth Browser Automation)  
> **Default Daily Cap:** 50 submissions / 24 hours  

---

## 1. Prerequisites & Session Context

Naukri requires authenticated browser sessions protected by OTP / CAPTCHA challenges during initial login. JoBot decouples interactive login from automated execution.

### Interactive Login Flow
1. Run the interactive login CLI command:
   ```bash
   jobot login naukri
   ```
2. A headful Patchright browser window opens to the Naukri login page.
3. Enter credentials and complete the 2FA SMS/Email OTP verification when prompted.
4. Once logged in, session cookies and storage context are serialized to `~/.jobot/sessions/naukri/state.json`.

---

## 2. Scraping & Requisition Ingestion

Search for opportunities matching candidate profile skills:
```bash
# Scrape matching postings and save to SQLite control plane
jobot scrape naukri --keywords "Senior Backend Engineer" --location "Bengaluru" --limit 25 --save
```

Postings are normalized with salary ranges, experience bands, and unique job IDs (`job_id = naukri:<id>`).

---

## 3. Application Execution Workflow

### Supervised Single Application
```bash
jobot apply <JOB_ID>
```
1. **Phases 1–9**: Validates candidate profile, maps contact details, extracts custom screening questions (e.g. Notice Period, Expected CTC), and validates answers against `CandidateTruthStore`.
2. **Phase 10 Approval Gate**: Suspends execution and presents drafted form values in the terminal / GUI approval inbox.
3. **Phase 11–12 Dispatch**:
   ```bash
   jobot apply <JOB_ID> --approve
   ```
   - Spawns persistent browser context from stored session.
   - Navigates to application URL with randomized mouse curves.
   - Fills question answers, selects tailored resume PDF, and clicks Submit.
   - Captures DOM confirmation receipt and saves full screenshot to `~/.jobot/evidence/`.

### Live Browser Execution Requirements
Ensure live browser mode is enabled:
```bash
export JOBOT_RUN_LIVE_BROWSER=1
```

---

## 4. Failure Recovery & Troubleshooting

### Scenario A: Session Expiration
- **Symptom**: Pipeline fails at Phase 11 with `AuthenticationExpiredError` or redirects to `/nlogin/login`.
- **Remediation**:
  ```bash
  jobot login --logout naukri
  jobot login naukri
  ```

### Scenario B: Circuit Breaker Tripped (`OPEN`)
- **Symptom**: Applications skipped with `CIRCUIT_OPEN` status due to consecutive network timeouts or Cloudflare blocks.
- **Remediation**:
  1. Inspect site health: `jobot site-health --site naukri`
  2. Inspect alerts: `jobot alerts --all`
  3. Acknowledge and allow cooldown: `jobot alerts --ack <ALERT_ID>`

