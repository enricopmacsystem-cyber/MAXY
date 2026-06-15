#!/usr/bin/env python3
"""
MAC AI Assistant — Build release Windows completa.

Pipeline:
  1. Legge desktop/version.json
  2. Genera version_info.txt + installer/version.iss
  3. Genera icona app.ico (se assente)
  4. PyInstaller → desktop/dist/MAC_AI_Assistant/
  5. Inno Setup  → dist/installer/MAC_AI_Assistant_Setup.exe
  6. Manifest release + checksum SHA256

Uso:
  python scripts/build_release.py
  python scripts/build_release.py --skip-installer
  python scripts/build_release.py --clean

Binari software (Connect .exe, APK Android) non sono nel repo Git — vengono copiati
in desktop/resources/software/ da ensure_software_assets() prima del bundle PyInstaller.
Fonti: ~/Downloads/softwares pack/, Desktop, android/app/build/outputs/apk/release/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = PROJECT_ROOT / "desktop"
DIST_HUB = DESKTOP_ROOT / "dist" / "MAC_AI_Hub"
DIST_INSTALLER = PROJECT_ROOT / "dist" / "installer"
BUILD_DIR = DESKTOP_ROOT / "build"
SPEC_FILE = DESKTOP_ROOT / "mac_ai_assistant.spec"
HUB_SPEC_FILE = DESKTOP_ROOT / "mac_ai_hub.spec"
VERSION_JSON = DESKTOP_ROOT / "version.json"
VERSION_ISS = DESKTOP_ROOT / "installer" / "version.iss"
RELEASE_DIR = PROJECT_ROOT / "dist" / "release"


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, check=check)


def load_version() -> dict:
    return json.loads(VERSION_JSON.read_text(encoding="utf-8"))


def product_title(meta: dict) -> str:
    return str(meta.get("product_title", "Maxy 2.0 - daisy"))


def dist_app_dir(meta: dict) -> Path:
    return DESKTOP_ROOT / "dist" / product_title(meta)


def app_exe_path(meta: dict) -> Path:
    return dist_app_dir(meta) / f"{product_title(meta)}.exe"


def installer_exe_path(meta: dict) -> Path:
    return DIST_INSTALLER / f"{product_title(meta)}.exe"


def write_version_iss(meta: dict) -> None:
    version = meta["version"]
    build = int(meta.get("build", 1))
    parts = version.split(".")
    while len(parts) < 4:
        parts.append("0")
    full = ".".join(parts[:3] + [str(build)])
    title = product_title(meta)
    publisher = meta.get("publisher", "MacSystem s.r.l.")
    developer = meta.get("developer", "Andrea Santin")
    content = f"""; Generato da scripts/build_release.py — {datetime.now(UTC).isoformat()}
#define MyAppVersion "{version}"
#define MyAppVersionFull "{full}"
#define MyAppBuild {build}
#define MyAppProductName "{title}"
#define MyAppPublisher "{publisher}"
#define MyAppDeveloper "{developer}"
#define MyAppExeName "{title}.exe"
#define MyAppOutputBase "{title}"
#define MyAppSourceDir "..\\dist\\{title}"
"""
    VERSION_ISS.write_text(content, encoding="utf-8")
    print(f"Aggiornato: {VERSION_ISS}")


def ensure_software_assets() -> None:
    """Copia Connect e APK Android in desktop/resources/software per il bundle."""
    software_dir = DESKTOP_ROOT / "resources" / "software"
    software_dir.mkdir(parents=True, exist_ok=True)

    connect_sources = [
        Path.home() / "Downloads" / "softwares pack" / "macsystemconnect.exe",
        PROJECT_ROOT / "desktop" / "resources" / "software" / "macsystemconnect.exe",
    ]
    connect_dest = software_dir / "macsystemconnect.exe"
    for source in connect_sources:
        if source.is_file():
            if not connect_dest.exists() or source.stat().st_mtime > connect_dest.stat().st_mtime:
                shutil.copy2(source, connect_dest)
                print(f"Copiato Connect: {connect_dest}")
            break

    desktop_apk = Path.home() / "Desktop" / "MacSystem-2.0.1-Dandelion.apk"
    apk_sources = [
        desktop_apk,
        PROJECT_ROOT / "dist" / "MacSystem-2.0.1-Dandelion.apk",
        PROJECT_ROOT / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk",
        software_dir / "MacSystem-2.0.1-Dandelion.apk",
        software_dir / "MacSystem-App.apk",
    ]
    apk_dest = software_dir / "MacSystem-2.0.1-Dandelion.apk"
    for source in apk_sources:
        if source.is_file():
            if not apk_dest.exists() or source.stat().st_mtime > apk_dest.stat().st_mtime:
                shutil.copy2(source, apk_dest)
                print(f"Copiato APK Android: {apk_dest}")
            break


def ensure_icon() -> None:
    resources = DESKTOP_ROOT / "resources"
    icon = resources / "app.ico"
    source = resources / "logo-m.png"
    script = resources / "generate_app_icon.py"
    needs_build = not icon.exists()
    if source.exists() and (needs_build or source.stat().st_mtime > icon.stat().st_mtime):
        needs_build = True
    if needs_build and script.exists():
        run([sys.executable, str(script)])


def generate_version_info() -> None:
    run([sys.executable, str(DESKTOP_ROOT / "generate_version_info.py")])


def install_build_deps() -> None:
    run([sys.executable, "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")])
    run([sys.executable, "-m", "pip", "install", "-r", str(DESKTOP_ROOT / "requirements.txt")])
    run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.6.0"])


def build_pyinstaller(meta: dict, *, clean: bool) -> Path:
    dist_app = dist_app_dir(meta)
    if clean:
        for path in (BUILD_DIR, DESKTOP_ROOT / "dist"):
            if path.exists():
                shutil.rmtree(path)
                print(f"Rimosso: {path}")

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

    exe = app_exe_path(meta)
    if not exe.exists():
        raise FileNotFoundError(f"Build PyInstaller fallita — manca {exe}")
    print(f"\n[OK] Applicazione: {exe}")
    print(f"     Cartella dist: {dist_app}")
    return exe


def build_hub_pyinstaller(*, clean: bool) -> Path:
    if clean and DIST_HUB.exists():
        shutil.rmtree(DIST_HUB)
        print(f"Rimosso: {DIST_HUB}")

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(HUB_SPEC_FILE),
        ],
        cwd=DESKTOP_ROOT,
    )

    exe = DIST_HUB / "MAC_AI_Hub.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Build Hub fallita — manca {exe}")
    print(f"\n[OK] Integration Hub: {exe}")
    return exe


def find_iscc() -> str | None:
    """Trova ISCC.exe (Inno Setup Compiler)."""
    env_dir = os.environ.get("INNO_SETUP_DIR", "").strip()
    candidates: list[Path] = []
    if env_dir:
        candidates.append(Path(env_dir) / "ISCC.exe")
    for path in (
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Inno Setup 6\ISCC.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ):
        candidates.append(Path(path))
    which = shutil.which("ISCC") or shutil.which("iscc")
    if which:
        return which
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def build_inno_setup(meta: dict) -> Path | None:
    iscc = find_iscc()
    iss = DESKTOP_ROOT / "installer" / "setup.iss"
    if not iscc:
        print("\n[WARN] Inno Setup non trovato (ISCC.exe)")
        print("       Impostare variabile INNO_SETUP_DIR oppure aggiungere ISCC al PATH")
        print("       Esempio: $env:INNO_SETUP_DIR='C:\\Program Files (x86)\\Inno Setup 6'")
        return None
    print(f"Usando Inno Setup: {iscc}")

    DIST_INSTALLER.mkdir(parents=True, exist_ok=True)
    run([iscc, str(iss)])

    setup = installer_exe_path(meta)
    if setup.exists():
        print(f"\n[OK] Installer: {setup}")
        return setup

    title = product_title(meta)
    alt = list((DESKTOP_ROOT / "installer" / "Output").glob(f"{title}*.exe"))
    if alt:
        shutil.copy2(alt[0], setup)
        print(f"\n[OK] Installer copiato: {setup}")
        return setup

    raise FileNotFoundError("Installer non generato da Inno Setup")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_release_manifest(meta: dict, setup: Path | None, app_exe: Path) -> Path:
    dist_app = dist_app_dir(meta)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    version = meta["version"]
    build = meta.get("build", 1)

    manifest = {
        "name": meta.get("name", "Maxy AI"),
        "product_title": product_title(meta),
        "version": version,
        "build": build,
        "published_at": datetime.now(UTC).isoformat(),
        "publisher": meta.get("publisher", "MacSystem s.r.l."),
        "developer": meta.get("developer", "Andrea Santin"),
        "artifacts": {},
    }

    if app_exe.exists():
        manifest["artifacts"]["portable_dir"] = str(dist_app.relative_to(PROJECT_ROOT))
        manifest["artifacts"]["exe_sha256"] = sha256_file(app_exe)

    if setup and setup.exists():
        manifest["artifacts"]["installer"] = str(setup.relative_to(PROJECT_ROOT))
        manifest["artifacts"]["installer_sha256"] = sha256_file(setup)
        manifest["download_url"] = meta.get(
            "update_url", ""
        ).replace("manifest.json", f"{product_title(meta)}.exe")

    manifest_path = RELEASE_DIR / f"manifest_{version}_b{build}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    latest = RELEASE_DIR / "manifest.json"
    latest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n[OK] Manifest: {manifest_path}")
    return manifest_path


def print_summary(meta: dict, setup: Path | None, app_exe: Path) -> None:
    print("\n" + "=" * 60)
    print(f"  BUILD COMPLETATA — {product_title(meta)}")
    print("=" * 60)
    print(f"  Applicazione:  {app_exe}")
    print(f"  Dist folder:   {dist_app_dir(meta)}")
    if setup:
        size_mb = setup.stat().st_size / (1024 * 1024)
        print(f"  Installer:     {setup}  ({size_mb:.1f} MB)")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build release Windows MAC AI Assistant")
    parser.add_argument("--skip-installer", action="store_true", help="Solo PyInstaller, senza Inno Setup")
    parser.add_argument("--clean", action="store_true", help="Pulisci build/dist prima della compilazione")
    parser.add_argument("--skip-deps", action="store_true", help="Non reinstallare dipendenze pip")
    args = parser.parse_args()

    meta = load_version()
    print(f"Build {meta.get('name')} v{meta.get('version')} (build {meta.get('build')})")

    write_version_iss(meta)
    ensure_icon()
    ensure_software_assets()
    generate_version_info()

    if not args.skip_deps:
        install_build_deps()

    app_exe = build_pyinstaller(meta, clean=args.clean)
    build_hub_pyinstaller(clean=False)

    if dist_app_dir(meta).exists():
        run([sys.executable, str(PROJECT_ROOT / "scripts" / "clean_dist.py")])

    setup = None
    if not args.skip_installer:
        setup = build_inno_setup(meta)

    write_release_manifest(meta, setup, app_exe)
    print_summary(meta, setup, app_exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
