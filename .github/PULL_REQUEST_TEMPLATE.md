## Summary

One or two sentences: what this pull request does and why.

## Related issue

Link the issue this PR resolves or advances (for example, `Closes #123`).
If there is no issue, explain why this change is needed.

## What changed

Bullet list of behavioral and structural changes (files/modules touched and
what they now do differently). Note any interface contracts affected —
`docs/contracts.md` freezes public interfaces; changes there need an
addendum.

## How it was verified

Exact commands you ran and their summarized results. Evidence, not assertion
(see CONTRIBUTING.md, "Verification-First Culture").

```text
python -m pytest -q        # e.g. 372 passed, 3 skipped
ruff check src/            # clean
mypy src/                  # no issues
npm test                   # vitest suites passing
npm run lint               # prettier clean
```

For behavior visible in the GUI or CLI, describe the manual check performed
(commands run, output observed). For adapter changes, state whether tests
cover live mode (`JOBOT_RUN_LIVE_BROWSER=1`) or mock/hermetic mode only.

## Checklist

- [ ] Tests added or updated for the change (or an explicit reason why not,
      with the manual evidence that replaces them)
- [ ] Documentation updated where behavior changed (SETUP.md, docs/, or
      docstrings as appropriate)
- [ ] No secrets, credentials, cookies, or personal data in this diff
- [ ] Changelog entry added under **Unreleased** in CHANGELOG.md if this is
      user-facing
- [ ] Adapters report honest no-op status when their live capability is
      disabled — no fabricated results
