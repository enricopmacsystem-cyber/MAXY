#!/usr/bin/env python3
"""Rimuove artefatti debug e componenti Qt non necessari prima dell'installer."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_JSON = PROJECT_ROOT / "desktop" / "version.json"
HUB_DIST = PROJECT_ROOT / "desktop" / "dist" / "MAC_AI_Hub" / "_internal"

REMOVE_SUFFIXES = {".obj", ".lib", ".prl", ".exp", ".pdb", ".pyi"}
# Non includere "resources": cancellerebbe splash e release_notes dell'app.
REMOVE_DIR_NAMES_UNDER_PYSIDE = {"qml", "translations", "resources"}
REMOVE_FILE_GLOBS = (
    "Qt6Quick*.dll",
    "Qt6Qml*.dll",
    "Qt6Labs*.dll",
    "Qt6Pdf*.dll",
    "Qt63D*.dll",
    "Qt6Charts*.dll",
    "Qt6DataVisualization*.dll",
    "Qt6Graphs*.dll",
    "Qt6Location*.dll",
    "Qt6Multimedia*.dll",
    "Qt6Positioning*.dll",
    "Qt6RemoteObjects*.dll",
    "Qt6Sensors*.dll",
    "Qt6SerialPort*.dll",
    "Qt6ShaderTools*.dll",
    "Qt6SpatialAudio*.dll",
    "Qt6StateMachine*.dll",
    "Qt6VirtualKeyboard*.dll",
    "Qt6Bluetooth*.dll",
    "Qt6Nfc*.dll",
    "Qt6Scxml*.dll",
)


def _product_dist_internal() -> Path:
    meta = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    title = meta.get("product_title", "Maxy 2.0 - daisy")
    return PROJECT_ROOT / "desktop" / "dist" / title / "_internal"


def _is_app_resources_dir(path: Path) -> bool:
    """Protegge resources/ con splash e release notes (non PySide6)."""
    if path.name != "resources":
        return False
    parent = path.parent.name.lower()
    return parent != "pyside6"


def _clean_tree(root: Path, *, label: str) -> tuple[int, int]:
    if not root.exists():
        print(f"[skip] {label}: cartella assente ({root})")
        return 0, 0

    removed_files = 0
    removed_dirs = 0

    for path in list(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in REMOVE_SUFFIXES:
            path.unlink(missing_ok=True)
            removed_files += 1

    for pyside_root in root.rglob("PySide6"):
        if not pyside_root.is_dir():
            continue
        for name in REMOVE_DIR_NAMES_UNDER_PYSIDE:
            target = pyside_root / name
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
                removed_dirs += 1

    for pattern in REMOVE_FILE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed_files += 1
        for path in root.rglob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed_files += 1

    for tests_dir in root.rglob("numpy"):
        tests_path = tests_dir / "tests"
        if tests_path.is_dir():
            shutil.rmtree(tests_path, ignore_errors=True)
            removed_dirs += 1

    print(f"Pulizia {label}: {removed_files} file, {removed_dirs} cartelle rimosse")
    return removed_files, removed_dirs


def clean() -> None:
    _clean_tree(_product_dist_internal(), label="applicazione")
    _clean_tree(HUB_DIST, label="hub")


if __name__ == "__main__":
    clean()
