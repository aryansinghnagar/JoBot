"""Build standalone Python sidecar binary for Tauri 2 desktop shell.

Uses PyInstaller to bundle `src/jobot/gui/sidecar.py` into a single standalone
executable placed in `gui/src-tauri/binaries/jobot-sidecar-${TARGET_TRIPLE}`.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def get_target_triple() -> str:
    """Return the Rust target triple for the current platform."""
    machine = platform.machine().lower()
    system = platform.system().lower()

    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "aarch64"
    else:
        arch = machine

    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    elif system == "darwin":
        return f"{arch}-apple-darwin"
    elif system == "linux":
        return f"{arch}-unknown-linux-gnu"
    else:
        return f"{arch}-unknown-{system}"


def build_sidecar() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    sidecar_entry = repo_root / "src" / "jobot" / "gui" / "sidecar.py"
    output_dir = repo_root / "gui" / "src-tauri" / "binaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    target_triple = get_target_triple()
    ext = ".exe" if sys.platform == "win32" else ""
    target_filename = f"jobot-sidecar-{target_triple}{ext}"
    final_output_path = output_dir / target_filename

    print(f"Building JoBot Sidecar binary for target: {target_triple}")
    print(f"Entrypoint: {sidecar_entry}")
    print(f"Destination: {final_output_path}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        f"jobot-sidecar-{target_triple}",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(output_dir),
        "--paths",
        str(repo_root / "src"),
        "--hidden-import",
        "jobot",
        "--hidden-import",
        "jobot.gui.sidecar",
        "--hidden-import",
        "pydantic",
        "--hidden-import",
        "cryptography",
        "--hidden-import",
        "keyring",
        "--hidden-import",
        "sqlite3",
        str(sidecar_entry),
    ]

    print("Running PyInstaller command:")
    print(" ".join(cmd))

    # Check if PyInstaller is installed
    try:
        import PyInstaller  # type: ignore # noqa: F401
    except ImportError:
        print("[WARN] PyInstaller is not installed in the current environment.")
        print("To build standalone binaries, run: pip install pyinstaller")
        print(f"[INFO] Target path configured: {final_output_path}")
        return

    result = subprocess.run(cmd, cwd=str(repo_root))
    if result.returncode == 0:
        print(f"✓ Standalone sidecar binary successfully built: {final_output_path}")
    else:
        print(f"✗ PyInstaller build failed with return code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build_sidecar()
