# RECURRING QUEUE — Periodic Routines

- [ ] Daily application loop execution (`jobot schedule daily`) — once scheduler robustness tests land (DST/missed-run/catch-up, R3.7).
- [ ] Weekly self-improvement eval sweep (run eval suites; compare against baseline; log regression deltas).
- [ ] Weekly site selector drift & adapter health audit (circuit-breaker states, healing events).
- [ ] Weekly dependency/security review (Dependabot, audit jobs, advisory feed).
- [ ] Monthly release train (semver release; CHANGELOG finalize; RC gates).
- [ ] Quarterly architecture review + external-intelligence digest (LangGraph, Temporal, Letta, PydanticAI, OpenHands, MCP ecosystem, provider/pricing changes) — adopt only via bounded local eval.
- [ ] Backup drill: restore-from-backup verification each release cycle.
