#!/usr/bin/env python3
"""
Pubblica una release per aggiornamenti automatici.

Copia MAC_AI_Assistant_Setup.exe e manifest.json nella cartella di output
e genera SQL per tabella app_releases (PostgreSQL hub).

Uso:
  python scripts/publish_release.py
  python scripts/publish_release.py --output \\server\updates\mac-ai-assistant
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_JSON = PROJECT_ROOT / "desktop" / "version.json"
INSTALLER = PROJECT_ROOT / "dist" / "installer" / "MAC_AI_Assistant_Setup.exe"
MANIFEST = PROJECT_ROOT / "dist" / "release" / "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dist" / "publish",
        help="Directory di pubblicazione",
    )
    parser.add_argument("--mandatory", action="store_true", help="Aggiornamento obbligatorio")
    args = parser.parse_args()

    if not INSTALLER.exists():
        raise SystemExit(f"Installer non trovato: {INSTALLER}\nEseguire prima build_release.py")

    meta = json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    version = meta["version"]
    args.output.mkdir(parents=True, exist_ok=True)

    dest_setup = args.output / "MAC_AI_Assistant_Setup.exe"
    shutil.copy2(INSTALLER, dest_setup)

    manifest_data = {}
    if MANIFEST.exists():
        manifest_data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_data["published_at"] = datetime.now(UTC).isoformat()
    manifest_data["mandatory"] = args.mandatory
    manifest_data["installer_file"] = dest_setup.name

    dest_manifest = args.output / "manifest.json"
    dest_manifest.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    download_url = meta.get("update_url", "").replace(
        "manifest.json", "MAC_AI_Assistant_Setup.exe"
    )
    sql = f"""
INSERT INTO app_releases (version, download_url, release_notes, mandatory)
VALUES (
    '{version}',
    '{download_url}',
    'Release {version} — MAC AI Assistant',
    {'TRUE' if args.mandatory else 'FALSE'}
)
ON CONFLICT (version) DO UPDATE SET
    download_url = EXCLUDED.download_url,
    release_notes = EXCLUDED.release_notes,
    mandatory = EXCLUDED.mandatory,
    published_at = NOW();
"""
    sql_path = args.output / f"release_{version}.sql"
    sql_path.write_text(sql.strip() + "\n", encoding="utf-8")

    print(f"Pubblicato: {dest_setup}")
    print(f"Manifest:   {dest_manifest}")
    print(f"SQL:        {sql_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
