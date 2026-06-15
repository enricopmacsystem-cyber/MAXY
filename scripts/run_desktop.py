#!/usr/bin/env python3
"""Avvia client desktop PySide6."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = PROJECT_ROOT / "desktop"
sys.path.insert(0, str(DESKTOP_ROOT))

from mac_ai_assistant.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
