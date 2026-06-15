---
name: maxy-release
description: >-
  Builds and validates Maxy AI Windows releases: version bump, PyInstaller,
  Inno Setup installer, manifest. Use for build_release, installer, version bump,
  or publishing a new daisy build.
disable-model-invocation: true
---

# Maxy — Build & release

## Versione

- `desktop/version.json` — `version`, `build`, `product_title`
- `desktop/installer/hub.env.default` — `APP_CURRENT_VERSION` allineato a `version`
- `desktop/resources/release_notes_it.txt` — sezione nuova build

## Build

```powershell
cd c:\MAXY
python scripts/build_release.py --skip-deps
```

Opzioni: `--clean`, `--skip-installer`

## Output attesi

- `desktop/dist/Maxy 2.0 - daisy/Maxy 2.0 - daisy.exe`
- `desktop/dist/MAC_AI_Hub/MAC_AI_Hub.exe`
- `dist/installer/Maxy 2.0 - daisy.exe`
- `dist/release/manifest_*.json`

## Pre-release check

- [ ] `mac_ai_hub.spec` include hiddenimports per nuove lib Hub
- [ ] Hub health OK dopo install: database, technical_ai_configured
- [ ] Desktop: due modalità Maxy, richiesta tecnica non blocca UI
- [ ] Installer non sovrascrive `hub.env` esistente (`onlyifdoesntexist`)

## Bump build

Incrementa `build` in `version.json`; documenta in `release_notes_it.txt`.
