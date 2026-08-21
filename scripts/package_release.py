"""Automated release packaging, checksum generation, and artifact verification script.

Usage:
    python scripts/package_release.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from jobot import __version__


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"[RELEASE] Packaging JoBot v{__version__}...")

    # Build Python sdist and wheel
    cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(dist_dir), str(root)]
    print(f"[CMD] {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Wheel build failed:\n{res.stderr}", file=sys.stderr)
        return res.returncode

    # Compute SHA256 checksums
    checksum_lines: list[str] = []
    print("\n[ARTIFACTS]")
    for artifact in sorted(dist_dir.glob("*.whl")):
        sha = compute_sha256(artifact)
        size_kb = artifact.stat().st_size / 1024
        print(f"  • {artifact.name} ({size_kb:.1f} KB) -> {sha}")
        checksum_lines.append(f"{sha}  {artifact.name}")

    checksum_file = dist_dir / "SHA256SUMS.txt"
    checksum_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"\n[OK] Checksums written to: {checksum_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
