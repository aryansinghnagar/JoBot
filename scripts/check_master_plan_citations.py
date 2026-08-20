#!/usr/bin/env python3
"""Verify every MASTER_PLAN_EXPANDED.md citation in the repo resolves.

Audit fix JOB-V2-NEW-007 (docs-lint CI step): the post-remediation v2 audit
(``scripts/jobot_audit_v2.md``) found 5+ dangling section references —
``§3.4``, ``§9.2``, ``§12.5``, ``§13.2`` were cited in source files and
test docstrings but did not exist as sections in ``MASTER_PLAN_EXPANDED.md``.
``SECURITY.md`` cited "Section 8 (decided 2026-08-16) — D3" but D3 lives in
Section 5; "Section 2.5 (Non-goals v1)" but Non-goals lives in Section 2.4.

This script enforces that going forward:

1. Parse ``MASTER_PLAN_EXPANDED.md`` and collect every section header
   (``## Section N — Title`` and ``### N.M Subsection``).
2. Scan the repository (``src/``, ``tests/``, ``SECURITY.md``,
   ``CONTRIBUTING.md``, ``CHANGELOG.md``) for citations of the form
   ``MASTER_PLAN_EXPANDED.md §N.M``, ``MASTER_PLAN_EXPANDED.md §N``,
   ``MASTER_PLAN_EXPANDED.md Section N``, and the SECURITY.md-style
   bare ``MASTER_PLAN_EXPANDED.md`` followed by ``Section N`` within 80 chars.
3. For every citation, verify the referenced section exists. Report the
   file:line of any citation that does not resolve, and exit 1.

Usage:
    python scripts/check_master_plan_citations.py            # exit 1 on any unresolved citation
    python scripts/check_master_plan_citations.py --quiet    # only print failures

Exit codes: 0 = all citations resolve, 1 = one or more dangling citations,
2 = structural error (missing MASTER_PLAN file).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_PLAN = REPO_ROOT / "MASTER_PLAN_EXPANDED.md"

# Files / dirs to scan for citations.
SCAN_TARGETS = [
    "src",
    "tests",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "README.md",
    "SETUP.md",
    "docs",
]

# Audit fix JOB-V2-REG-002: ``src/jobot/storage/migrations.py`` is intentionally
# skipped because the migration apply-functions are checksummed (their source is
# hashed via ``inspect.getsource`` and recorded in the ``schema_migrations``
# table; any edit — including a docstring citation fix — raises
# ``MigrationError`` on existing installs). The dangling ``§13.2`` citation in
# ``_apply_003``'s docstring is documented in a comment immediately above the
# function; the corrected citation (``§8 WS5`` + ``§5 D18``) also lives in
# that comment.
SKIP_FILES: set[str] = {
    "src/jobot/storage/migrations.py",
}

# Section header patterns in MASTER_PLAN_EXPANDED.md.
# ``## Section N — Title``  -> defines top-level Section N
# ``### N.M Subsection``    -> defines subsection N.M
TOP_LEVEL_SECTION_RE = re.compile(r"^##\s+Section\s+(\d+)\b")
SUBSECTION_RE = re.compile(r"^###\s+(\d+\.\d+)\b")

# Citation patterns we look for in the rest of the repo.
# Matches "MASTER_PLAN_EXPANDED.md §N.M" or "MASTER_PLAN_EXPANDED.md §N" or
# "MASTER_PLAN_EXPANDED.md Section N.M" or "... Section N" within 80 chars.
CITATION_RES = [
    re.compile(r"MASTER_PLAN_EXPANDED\.md[^\n]{0,80}?§\s*(\d+(?:\.\d+)?)"),
    re.compile(r"MASTER_PLAN_EXPANDED\.md[^\n]{0,80}?Section\s+(\d+(?:\.\d+)?)"),
]


def parse_master_plan_sections(path: Path) -> set[str]:
    """Return the set of section IDs (e.g. ``3``, ``3.4``, ``6.2``) defined
    in the master plan."""
    if not path.exists():
        raise SystemExit(2)
    sections: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if m := TOP_LEVEL_SECTION_RE.match(line):
            sections.add(m.group(1))
        elif m := SUBSECTION_RE.match(line):
            sections.add(m.group(1))
    return sections


def iter_scan_files() -> list[Path]:
    out: list[Path] = []
    for rel in SCAN_TARGETS:
        path = REPO_ROOT / rel
        if path.is_dir():
            out.extend(path.rglob("*.py"))
            out.extend(path.rglob("*.md"))
        elif path.exists():
            out.append(path)
    # Deduplicate, skip the master plan itself, and skip the migration file
    # (see ``SKIP_FILES`` docstring).
    skip_abs = {(REPO_ROOT / rel).resolve() for rel in SKIP_FILES}
    out = sorted(
        {
            p
            for p in out
            if p.resolve() != MASTER_PLAN.resolve()
            and p.resolve() not in skip_abs
        }
    )
    return out


def collect_citations(files: list[Path]) -> list[tuple[Path, int, str, str]]:
    """Return list of (file, lineno, citation_text, section_id)."""
    out: list[tuple[Path, int, str, str]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for pat in CITATION_RES:
                for m in pat.finditer(line):
                    out.append((f, i, line.strip(), m.group(1)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quiet", action="store_true", help="only print failures, not the summary"
    )
    args = parser.parse_args()

    sections = parse_master_plan_sections(MASTER_PLAN)
    files = iter_scan_files()
    citations = collect_citations(files)

    failures: list[tuple[Path, int, str, str]] = []
    for f, lineno, line, sid in citations:
        if sid not in sections:
            failures.append((f, lineno, line, sid))

    if failures:
        print(
            f"FAIL: {len(failures)} citation(s) reference sections that do not exist "
            f"in {MASTER_PLAN.name}:",
            file=sys.stderr,
        )
        for f, lineno, line, sid in failures:
            rel = f.relative_to(REPO_ROOT) if f.is_absolute() else f
            print(f"  {rel}:{lineno}: §{sid}  ({line[:100]})", file=sys.stderr)
        print(
            f"\nDefined sections in {MASTER_PLAN.name}: "
            + ", ".join(sorted(sections, key=lambda x: tuple(int(p) for p in x.split(".")))),
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(
            f"OK: {len(citations)} citation(s) across {len(files)} files all resolve "
            f"to defined sections in {MASTER_PLAN.name}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
