#!/usr/bin/env python3
"""Copia ANTHROPIC_KEY da C:\\macsystem\\.env in hub.env come ANTHROPIC_API_KEY."""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    mac = Path(r"C:\macsystem\.env")
    appdata = os.getenv("APPDATA", "").strip()
    if not appdata:
        print("APPDATA non impostato")
        return 1
    hub = Path(appdata) / "MAC AI Assistant" / "hub.env"
    if not mac.is_file() or not hub.is_file():
        print("File sorgente o hub.env non trovato")
        return 1

    key = ""
    for line in mac.read_text(encoding="utf-8").splitlines():
        if line.startswith("ANTHROPIC_KEY="):
            key = line.partition("=")[2].strip().strip('"').strip("'")
            break
    if not key:
        print("ANTHROPIC_KEY non trovata in macsystem .env")
        return 1

    lines = hub.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("ANTHROPIC_API_KEY="):
            out.append(f"ANTHROPIC_API_KEY={key}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"ANTHROPIC_API_KEY={key}")
    hub.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("ANTHROPIC_API_KEY aggiornata in hub.env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
