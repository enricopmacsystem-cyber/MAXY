from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.pipeline.config import DIST_HUB, DIST_INSTALLER_DIR, PROJECT_ROOT, VERSION_JSON
from scripts.pipeline.report import PipelineReport


def run_release_gate(
    report: PipelineReport,
    *,
    skip_build: bool = False,
    skip_installer: bool = False,
    skip_deps: bool = True,
) -> None:
    report.phases.append("release")

    if skip_build:
        report.add("release", "info", "Build saltata (--skip-build)")
        _verify_artifacts(report)
        return

    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "build_release.py")]
    if skip_deps:
        cmd.append("--skip-deps")
    if skip_installer:
        cmd.append("--skip-installer")

    report.add("release", "info", "Avvio build_release.py (può richiedere 10–20 minuti)...")
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=False)
    if proc.returncode != 0:
        report.add("release", "error", f"build_release.py exit code {proc.returncode}")
        return

    _verify_artifacts(report)
    _smoke_test_hub(report)


def _verify_artifacts(report: PipelineReport) -> None:
    meta = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    title = meta.get("product_title", "Maxy 2.0 - daisy")
    app_exe = PROJECT_ROOT / "desktop" / "dist" / title / f"{title}.exe"
    hub_exe = DIST_HUB / "MAC_AI_Hub.exe"
    installer = DIST_INSTALLER_DIR / f"{title}.exe"

    for path, label in (
        (app_exe, "Desktop exe"),
        (hub_exe, "Hub exe"),
        (installer, "Installer"),
    ):
        if path.is_file():
            mb = path.stat().st_size / (1024 * 1024)
            report.add("release", "info", f"{label}: {path} ({mb:.1f} MB)")
        else:
            report.add("release", "warn" if label == "Installer" else "error", f"Manca {label}: {path}")


def _smoke_test_hub(report: PipelineReport) -> None:
    hub_exe = DIST_HUB / "MAC_AI_Hub.exe"
    if not hub_exe.is_file():
        return
    try:
        proc = subprocess.run(
            [str(hub_exe), "--init-db"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0 and "pydoc" in (proc.stderr + proc.stdout).lower():
            report.add("release", "error", "Hub exe: errore pydoc/NLTK all'avvio")
        elif proc.returncode != 0:
            report.add(
                "release",
                "warn",
                f"Hub --init-db exit {proc.returncode} (verificare PostgreSQL attivo)",
            )
        else:
            report.add("release", "info", "Smoke test Hub --init-db OK")
    except subprocess.TimeoutExpired:
        report.add("release", "warn", "Hub --init-db timeout (120s)")
