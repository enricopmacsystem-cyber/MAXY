from __future__ import annotations

import re
from pathlib import Path

from scripts.pipeline.config import (
    API_KEY_PATTERNS,
    PROJECT_ROOT,
    SCAN_DIRS,
    SECRET_KEY_NAMES,
    SECURITY_ALLOWLIST_SUBSTRINGS,
    SKIP_PATH_PARTS,
)
from scripts.pipeline.report import PipelineReport

TRACKED_SECRET_FILES = (
    "hub.env",
    ".env",
    "credentials.json",
    "secrets.json",
)


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for name in SCAN_DIRS:
        root = PROJECT_ROOT / name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            if any(part in rel for part in SKIP_PATH_PARTS):
                continue
            if path.suffix.lower() not in {".py", ".ps1", ".ini", ".env", ".json", ".mdc", ".md"}:
                continue
            files.append(path)
    return files


def run_security_scan(report: PipelineReport) -> None:
    report.phases.append("security")

    for rel in TRACKED_SECRET_FILES:
        for path in PROJECT_ROOT.rglob(rel):
            if "dist" in path.parts or "build" in path.parts:
                continue
            if path.name == "hub.env.default":
                continue
            report.add(
                "security",
                "error",
                f"File sensibile nel repo: {path.relative_to(PROJECT_ROOT)}",
                str(path),
            )

    patterns = [re.compile(p, re.IGNORECASE) for p in API_KEY_PATTERNS]
    key_assign = re.compile(
        r"^\s*(" + "|".join(SECRET_KEY_NAMES) + r")\s*=\s*(\S+)\s*$"
    )
    for path in _iter_source_files():
        rel = path.relative_to(PROJECT_ROOT)
        rel_s = str(rel).replace("\\", "/")
        if any(allow in rel_s for allow in SECURITY_ALLOWLIST_SUBSTRINGS):
            continue
        if path.name == "hub.env.default":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            m = key_assign.match(line)
            if m:
                value = m.group(2).strip("\"'")
                if value and "..." not in value and len(value) >= 12:
                    report.add(
                        "security",
                        "error",
                        f"Chiave segreta con valore in chiaro: {m.group(1)}",
                        str(rel),
                    )
                    break
        for pat in patterns:
            if pat.search(text):
                report.add(
                    "security",
                    "error",
                    f"Possibile API key hardcoded ({pat.pattern})",
                    str(rel),
                )
                break

    hub_env_default = PROJECT_ROOT / "desktop" / "installer" / "hub.env.default"
    if hub_env_default.is_file():
        text = hub_env_default.read_text(encoding="utf-8")
        for key in ("ANTHROPIC_API_KEY=", "GEMINI_API_KEY=", "GMAIL_CLIENT_SECRET="):
            for line in text.splitlines():
                if line.startswith(key) and line.split("=", 1)[1].strip():
                    report.add(
                        "security",
                        "error",
                        "hub.env.default non deve contenere chiavi reali",
                        str(hub_env_default),
                    )

    main_py = PROJECT_ROOT / "app" / "main.py"
    if main_py.is_file() and 'allow_origins=["*"]' in main_py.read_text(encoding="utf-8"):
        report.add(
            "security",
            "warn",
            "CORS allow_origins=* su Hub locale — accettabile per desktop, verificare in deploy remoto",
            "app/main.py",
        )

    if not report.errors():
        report.add("security", "info", "Scan segreti automatico: nessun errore bloccante")
