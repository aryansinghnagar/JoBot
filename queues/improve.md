# IMPROVE QUEUE — Unwired Subsystems to Integrate

The following 9 implemented subsystems are queued for full pipeline integration during Phase 1:

1. **`QAEngine`** (`src/jobot/ai/qa_engine.py`): Wire into ASP Phase 4&5 and Phase 6&7 for dynamic form question answering.
2. **`PolicyEngine`** (`src/jobot/policy/engine.py`): Wire into campaign runner for daily cap enforcement and supervised gates.
3. **`CircuitBreaker`** (`src/jobot/failure/catalog.py`): Wire around adapter submit/verify calls to handle per-site failures.
4. **`TraceLogger`** (`src/jobot/obs/tracing.py`): Wire into pipeline phases to emit persistent JSONL spans.
5. **`AlertDispatcher`** (`src/jobot/obs/alerts.py`): Wire into PolicyEngine and CircuitBreaker for incident alerting.
6. **`EightTierMemorySystem`** (`src/jobot/memory/system.py`): Persist form_field_memory tier for field mapping reuse.
7. **`BehavioralMimicry`** (`src/jobot/stealth/behavior.py`): Fix Bezier curve math and wire into browser automation adapters.
8. **`ProxyManager`** (`src/jobot/stealth/proxy.py`): Wire into browser context initialization.
9. **`CaptchaSolver`** (`src/jobot/stealth/captcha.py`): Wire multimodal image bytes to LLM vision API.
