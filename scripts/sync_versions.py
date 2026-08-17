#!/usr/bin/env python3
"""Sync the canonical package version from pyproject.toml to every manifest.

Source of truth: pyproject.toml [project] version.
Consumers: root package.json, gui/package.json, gui/src-tauri/tauri.conf.json,
gui/src-tauri/Cargo.toml.

Usage:
    python scripts/sync_versions.py           # write versions into consumers
    python scripts/sync_versions.py --check   # exit 1 on drift (CI mode)

Exit codes: 0 = in sync (or synced), 1 = drift detected in --check mode,
2 = structural error (missing file / unparsable manifest).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
JSON_CONSUMERS = [
    REPO_ROOT / "package.json",
    REPO_ROOT / "gui" / "package.json",
    REPO_ROOT / "gui" / "src-tauri" / "tauri.conf.json",
]
CARGO_TOML = REPO_ROOT / "gui" / "src-tauri" / "Cargo.toml"


def canonical_version() -> str:
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    version = data.get("project", {}).get("version")
    if not version or not isinstance(version, str):
        raise SystemExit(2)
    return version


def read_consumer_versions() -> dict[Path, str | None]:
    versions: dict[Path, str | None] = {}
    for path in JSON_CONSUMERS:
        if not path.exists():
            versions[path] = None
            continue
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        versions[path] = data.get("version")

    if CARGO_TOML.exists():
        with CARGO_TOML.open("rb") as f:
            data = tomllib.load(f)
        versions[CARGO_TOML] = data.get("package", {}).get("version")
    else:
        versions[CARGO_TOML] = None

    return versions


def write_consumer_version(path: Path, version: str) -> None:
    if path == CARGO_TOML:
        content = path.read_text(encoding="utf-8")
        updated = re.sub(
            r'(?m)^version\s*=\s*"[^"]*"',
            f'version = "{version}"',
            content,
            count=1,
        )
        path.write_text(updated, encoding="utf-8", newline="\n")
        return

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = version
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on drift; write nothing")
    args = parser.parse_args()

    if not PYPROJECT.exists():
        print(f"error: {PYPROJECT} not found", file=sys.stderr)
        return 2

    version = canonical_version()
    current = read_consumer_versions()
    drifted = [p for p, v in current.items() if v != version]

    if args.check:
        if drifted:
            print(f"version drift detected (canonical pyproject: {version}):")
            for path in drifted:
                print(f"  {path.relative_to(REPO_ROOT)}: {current[path]!r}")
            print("run: python scripts/sync_versions.py")
            return 1
        print(f"versions in sync at {version}")
        return 0

    for path in drifted:
        write_consumer_version(path, version)
        print(f"synced {path.relative_to(REPO_ROOT)} -> {version}")
    if not drifted:
        print(f"versions already in sync at {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
