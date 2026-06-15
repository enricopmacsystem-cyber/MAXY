#!/usr/bin/env python3
"""DEPRECATO — usare scripts/build_release.py per build completa."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = PROJECT_ROOT / "desktop"
DIST_DIR = DESKTOP_ROOT / "dist"
BUILD_DIR = DESKTOP_ROOT / "build"
SPEC_FILE = DESKTOP_ROOT / "mac_ai_assistant.spec"
INSTALLER_DIR = PROJECT_ROOT / "dist" / "installer"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(f">>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=True)


def build_pyinstaller() -> Path:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(SPEC_FILE),
        ],
        cwd=DESKTOP_ROOT,
    )
    exe = DIST_DIR / "MAC_AI_Assistant.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Build fallita: {exe} non trovato")
    print(f"Build completata: {exe}")
    return exe


def build_inno_setup() -> Path | None:
    iscc = shutil.which("ISCC") or shutil.which("iscc")
    iss = DESKTOP_ROOT / "installer" / "setup.iss"
    if not iscc:
        print("Inno Setup (ISCC) non trovato — salto creazione Setup.exe")
        print("Installa Inno Setup 6 e aggiungi ISCC al PATH")
        return None
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    run([iscc, str(iss)])
    setups = list(INSTALLER_DIR.glob("MAC_AI_Assistant_Setup_*.exe"))
    if setups:
        print(f"Installer creato: {setups[0]}")
        return setups[0]
    output = list((DESKTOP_ROOT / "installer" / "Output").glob("*.exe"))
    if output:
        dest = INSTALLER_DIR / output[0].name
        shutil.copy2(output[0], dest)
        print(f"Installer copiato: {dest}")
        return dest
    return None


def main() -> None:
    print("DEPRECATO: usare python scripts/build_release.py")
    run([sys.executable, str(PROJECT_ROOT / "scripts" / "build_release.py")])


if __name__ == "__main__":
    main()
