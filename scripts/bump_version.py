"""Version bump utility for JoBot.

Updates the canonical version in `pyproject.toml` and invokes
`scripts/sync_versions.py` to propagate the new version across all manifests.

Usage:
    python scripts/bump_version.py 1.0.0
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def bump_version(new_version: str) -> None:
    # Validate semver format
    if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", new_version):
        print(f"error: invalid semver format: {new_version}", file=sys.stderr)
        sys.exit(1)

    content = PYPROJECT.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version\s*=\s*"[^"]*"',
        f'version = "{new_version}"',
        content,
        count=1,
    )
    if count == 0:
        print("error: could not find version in pyproject.toml", file=sys.stderr)
        sys.exit(2)

    PYPROJECT.write_text(updated, encoding="utf-8", newline="\n")
    print(f"Updated pyproject.toml -> {new_version}")

    # Synchronize all consumer manifests
    sync_script = REPO_ROOT / "scripts" / "sync_versions.py"
    subprocess.run([sys.executable, str(sync_script)], check=True)
    print(f"[OK] All manifests successfully bumped to version {new_version}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        sys.exit(1)
    bump_version(sys.argv[1].strip())
