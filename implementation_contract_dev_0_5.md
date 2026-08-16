# Implementation Contract: Milestone dev-0.5 (Essential Features)

**Document ID**: CONTRACT-DEV-0.5  
**Version**: 1.0  
**Status**: Implemented & Verified  
**Target Completion**: Milestone dev-0.5  

---

## 1. Objective
Add 5 portal adapters (Naukri, LinkedIn, Indeed, Greenhouse, Lever), provider-neutral LLM `ModelRouter` (Gemini, OpenAI, Anthropic, Ollama), Form Q&A Engine with grounding checks and prompt-injection defense, `PolicyEngine` with 9 default security policies, and CLI scheduling functionality.

## 2. Completed Scope
1. **LLM & Q&A Engine** (`src/jobaut/ai/`):
   - `ModelRouter`: Gemini 2.5/3.0 primary integration (`google-genai`), OpenAI/Anthropic/Ollama fallbacks, daily budget tracking & cost logging.
   - `QAEngine`: Question classification (`PROFILE_DIRECT`, `BEHAVIORAL`, `SENSITIVE`, `UNANSWERABLE`), candidate profile direct retrieval, profile grounding verification gate, and prompt-injection sanitization.
2. **Site Adapters** (`src/jobaut/adapters/`):
   - `LinkedInAdapter` (Camoufox engine, stealth headers, rate limits)
   - `IndeedAdapter` (Indeed.com flow)
   - `GreenhouseAdapter` (Greenhouse ATS API & form submission)
   - `LeverAdapter` (Lever ATS API & form submission)
   - `NaukriAdapter` & `MockATSAdapter`
3. **Governance & Security PolicyEngine** (`src/jobaut/policy/`):
   - 9 default safety & governance policies (max daily applications, grounding failure checks, sensitive field exclusion, rate-limiting, secret redaction, circuit breakers).
4. **CLI Polish** (`src/jobaut/cli/`):
   - Multi-site support (`naukri`, `linkedin`, `indeed`, `greenhouse`, `lever`, `mock_ats`)
   - `jobaut schedule`: Automated background apply scheduling

## 3. Exit Criteria Verification
- [x] 5 Site Adapters operational with rate-limiting and jitter
- [x] `ModelRouter` provider abstraction with budget tracking
- [x] `QAEngine` with profile grounding verification and prompt injection defense
- [x] `PolicyEngine` with 9 default rules
- [x] CLI `schedule` command
- [x] Automated test suite passing 100%
