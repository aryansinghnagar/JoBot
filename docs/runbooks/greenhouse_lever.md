# Operational Runbook: Direct API Execution (Greenhouse & Lever)

> **Target Platforms:** Greenhouse (oards.greenhouse.io), Lever (jobs.lever.co)  
> **Adapter Classes:** GreenhouseAdapter, LeverAdapter (src/jobot/adapters/)  
> **Capability Tier:** Level 4 (Direct REST/JSON Submission API)  
> **Latency:** ~300ms–800ms per submission (Zero browser overhead)  

---

## 1. Overview & Mechanics

Greenhouse and Lever host public career board APIs that accept direct multipart form POST submissions. JoBot interacts with these endpoints natively via Python HTTP clients without launching browser processes.

### Key Advantages
- **Determinism**: Submissions receive synchronous HTTP response payloads (200 OK or structured 400 Bad Request validation errors).
- **Zero Stealth Overhead**: Operates over standard public ATS REST endpoints without browser fingerprinting concerns.
- **High Throughput**: Ideal for batch applications and continuous campaign execution.

---

## 2. Scraping & Requisition Ingestion

Direct ATS scraping queries the employer's board token:

`ash
# Scrape Greenhouse boards for target companies
jobot scrape greenhouse --companies stripe,airbnb,cloudflare,datadog --save

# Scrape Lever postings
jobot scrape lever --companies netflix,spotify,figma --save
`

---

## 3. Application Execution Workflow

### Supervised Application
`ash
# 1. Evaluate matching and draft form fields
jobot apply <JOB_ID>

# 2. Review generated resume, cover letter, and Q&A answers in CLI/GUI

# 3. Submit directly over HTTPS
jobot apply <JOB_ID> --approve
`

### Form Payload Assembly
The adapter automatically constructs the multipart/form-data payload:
1. irst_name, last_name, email, phone
2. 
esume: Uploads dynamically compiled PDF (DocumentTailor output)
3. cover_letter: Injects tailored text or attaches PDF
4. urls[LinkedIn], urls[GitHub], urls[Portfolio]
5. custom_questions: Form questions answered via QAEngine

---

## 4. Verification & Non-Repudiation

Upon HTTP POST:
- **Greenhouse**: Asserts 
esponse.status_code in (200, 201) and parses confirmation JSON.
- **Lever**: Asserts 
esponse.status_code == 200 and extracts Lever application ID.
- Evidence item with response body and SHA-256 digest is persisted in SQLite evidence table.
