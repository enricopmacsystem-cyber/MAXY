# -*- mode: python ; coding: utf-8 -*-
# Integration Hub locale — PyInstaller onedir
# Output: desktop/dist/MAC_AI_Hub/MAC_AI_Hub.exe

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent
ENTRY = PROJECT_ROOT / "scripts" / "hub_entry.py"
DATABASE_DIR = PROJECT_ROOT / "database"

block_cipher = None

datas = []
if DATABASE_DIR.is_dir():
    datas.append((str(DATABASE_DIR), "database"))

hiddenimports = collect_submodules("app") + [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "psycopg2",
    "psycopg2._psycopg",
    "sqlalchemy.dialects.postgresql",
    "app.main",
    "app.api.router",
    "app.config.settings",
    "app.db.session",
    "app.integrations.easyone.auth_client",
    "app.integrations.easyone.macsystem_auth",
    "app.services.auth_service",
    "google.genai",
    "google.genai.types",
    "app.integrations.gemini.chat",
    "app.integrations.gemini.embeddings",
    "app.integrations.gemini.client",
    "app.core.exceptions",
    "app.api.routes.auth",
    "app.integrations.macsystem_bot",
    "app.integrations.macsystem_bot.adapter",
    "app.integrations.macsystem_bot.bot_engine",
    "anthropic",
    "chromadb",
    "sentence_transformers",
    "certifi",
    "pydoc",
]

datas += collect_data_files("certifi")

a = Analysis(
    [str(ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(Path(SPECPATH) / "hooks" / "runtime_hub_stdio.py")],
    excludes=[
        "tkinter",
        "matplotlib",
        "PySide6",
        "pytest",
        "numpy.testing",
        "unittest",
        "doctest",
        "IPython",
        "notebook",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MAC_AI_Hub",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MAC_AI_Hub",
)
