from __future__ import annotations

import compileall
import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.pipeline.config import (
    APP_DIR,
    DESKTOP_DIR,
    HUB_SPEC,
    PROJECT_ROOT,
    SCRIPTS_DIR,
    VERSION_JSON,
)
from scripts.pipeline.report import PipelineReport


def run_preflight(report: PipelineReport) -> None:
    report.phases.append("preflight")

    if not VERSION_JSON.is_file():
        report.add("preflight", "error", "Manca desktop/version.json")
        return

    try:
        meta = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
        build = int(meta.get("build", 0))
        if build < 1:
            report.add("preflight", "error", "build non valido in version.json")
        else:
            report.add(
                "preflight",
                "info",
                f"Versione {meta.get('version')} build {build} ({meta.get('build_name')})",
            )
    except Exception as exc:
        report.add("preflight", "error", f"version.json non leggibile: {exc}")

    if not compileall.compile_dir(str(APP_DIR), quiet=1):
        report.add("preflight", "error", "Errori di compilazione in app/")
    else:
        report.add("preflight", "info", "Compile OK: app/")

    desktop_pkg = DESKTOP_DIR / "mac_ai_assistant"
    if desktop_pkg.is_dir():
        if not compileall.compile_dir(str(desktop_pkg), quiet=1):
            report.add("preflight", "error", "Errori di compilazione in desktop/mac_ai_assistant/")
        else:
            report.add("preflight", "info", "Compile OK: desktop/mac_ai_assistant/")

    if HUB_SPEC.is_file():
        spec_text = HUB_SPEC.read_text(encoding="utf-8")
        if re.search(r"excludes\s*=\s*\[[^\]]*[\"']pydoc[\"']", spec_text, re.DOTALL):
            report.add(
                "preflight",
                "error",
                "mac_ai_hub.spec esclude pydoc (rompe NLTK/Hub exe)",
                str(HUB_SPEC),
            )
        elif '"pydoc"' not in spec_text:
            report.add(
                "preflight",
                "warn",
                "pydoc non elencato in mac_ai_hub.spec hiddenimports",
                str(HUB_SPEC),
            )
        else:
            report.add("preflight", "info", "mac_ai_hub.spec: pydoc configurato")

    try:
        proc = subprocess.run(
            [sys.executable, "-c", "import app.main; print('ok')"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            report.add("preflight", "error", f"import app.main fallito: {proc.stderr[:300]}")
        else:
            report.add("preflight", "info", "import app.main OK")
    except Exception as exc:
        report.add("preflight", "error", f"import app.main: {exc}")

    req = PROJECT_ROOT / "requirements.txt"
    if req.is_file():
        report.add("preflight", "info", "requirements.txt presente")
    else:
        report.add("preflight", "warn", "requirements.txt assente")

    if not (SCRIPTS_DIR / "build_release.py").is_file():
        report.add("preflight", "error", "Manca scripts/build_release.py")
