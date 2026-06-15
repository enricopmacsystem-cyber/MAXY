# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# MAC AI Assistant — PyInstaller spec (modalità onedir professionale)
# Output: desktop/dist/Maxy 2.0 - daisy/Maxy 2.0 - daisy.exe + _internal/
# Build:  python scripts/build_release.py
# =============================================================================

import json
from pathlib import Path

DESKTOP_ROOT = Path(SPECPATH)
RESOURCES = DESKTOP_ROOT / "resources"
ICON = RESOURCES / "app.ico" if (RESOURCES / "app.ico").exists() else None
VERSION_INFO = DESKTOP_ROOT / "version_info.txt"

block_cipher = None

# ---------------------------------------------------------------------------
# Dati inclusi nel bundle
# ---------------------------------------------------------------------------
datas = [
    (str(DESKTOP_ROOT / "installer" / "config.default.ini"), "installer"),
    (str(DESKTOP_ROOT / "version.json"), "."),
]
for asset in (
    "app.ico",
    "logo-m.png",
    "logo-m-header.png",
    "mac-system-banner.png",
    "mac-system-login-footer.png",
    "splash-maxy.png",
    "release_notes_it.txt",
):
    asset_path = RESOURCES / asset
    if asset_path.exists():
        datas.append((str(asset_path), "resources"))

software_dir = RESOURCES / "software"
if software_dir.is_dir():
    for item in sorted(software_dir.iterdir()):
        if item.is_file():
            datas.append((str(item), "resources/software"))

# ---------------------------------------------------------------------------
# Analisi dipendenze
# ---------------------------------------------------------------------------
a = Analysis(
    [str(DESKTOP_ROOT / "mac_ai_assistant" / "__main__.py")],
    pathex=[str(DESKTOP_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        # HTTP client
        "httpx",
        "httpcore",
        "h11",
        "h2",
        "anyio",
        "anyio._backends._asyncio",
        "sniffio",
        "certifi",
        "idna",
        "_cffi_backend",
        # stdlib extras
        "configparser",
        "json",
        "urllib.parse",
        "fpdf",
        "fpdf.html",
    ],
    hookspath=[str(DESKTOP_ROOT / "hooks")],
    hooksconfig={},
    runtime_hooks=[str(DESKTOP_ROOT / "hooks" / "runtime_mac_ai.py")]
    if (DESKTOP_ROOT / "hooks" / "runtime_mac_ai.py").exists()
    else [],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "pytest",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# EXE principale (onedir — binari in cartella _internal)
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Maxy 2.0 - daisy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON else None,
    version=str(VERSION_INFO) if VERSION_INFO.exists() else None,
)

# ---------------------------------------------------------------------------
# COLLECT — cartella dist completa
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Maxy 2.0 - daisy",
)
