---
name: Bug report
about: Something in JoBot behaved incorrectly or crashed
title: "[bug] "
labels: bug
assignees: ""
---

**What happened**

A clear and specific description of what went wrong. Include the exact error
message or unexpected output. If JoBot reported an honest no-op (for example
"live browser disabled"), that is expected behavior unless you set
`JOBOT_RUN_LIVE_BROWSER=1` — say so if you did.

**What you expected**

A clear description of what you expected to happen instead.

**Steps to reproduce**

1. Configuration used (profile name, relevant `jobot config` keys — values masked)
2. Exact command(s) run, or GUI actions taken
3. What happened at each step

Minimal reproductions get fixed fastest. If the bug involves a specific job
posting, include the job URL.

**Environment**

- OS and version:
- Python version (`python --version`):
- JoBot version (`pip show jobot` — the `Version:` line; or `jobot --version`):
- Node.js version, if the GUI is involved (`node --version`):
- How you run JoBot: CLI / `jobot sidecar` / Tauri desktop GUI / Docker

**Doctor output**

Paste the output of `jobot doctor` (redact anything sensitive):

```
(paste here)
```

**Logs with secrets redacted**

Relevant log excerpts or trace output. **Redact all secrets first**: API keys,
cookies, session tokens, passwords, and personal contact details must be
removed or masked (for example `AIzaSy***`).

```
(paste here)
```

**Adapter / site involved**

Which site adapter or component (for example: naukri, linkedin, workday,
greenhouse, lever, scrapers, documents/PDF, tracker, scheduler, sidecar,
GUI). Write "core" if it is not adapter-specific.
