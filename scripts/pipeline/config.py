from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = PROJECT_ROOT / "app"
DESKTOP_DIR = PROJECT_ROOT / "desktop"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DIST_HUB = DESKTOP_DIR / "dist" / "MAC_AI_Hub"
DIST_INSTALLER_DIR = PROJECT_ROOT / "dist" / "installer"
VERSION_JSON = DESKTOP_DIR / "version.json"
HUB_SPEC = DESKTOP_DIR / "mac_ai_hub.spec"
REPORTS_DIR = PROJECT_ROOT / "dist" / "pipeline-reports"

SECRET_KEY_NAMES = (
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GMAIL_CLIENT_SECRET",
    "MICROSOFT_CLIENT_SECRET",
)

API_KEY_PATTERNS = (
    r"sk-ant-[a-zA-Z0-9_-]{20,}",
    r"AIza[a-zA-Z0-9_-]{30,}",
)

# Path con riferimenti legittimi a password/URL (parametri, non segreti hardcoded)
SECURITY_ALLOWLIST_SUBSTRINGS = (
    "login_dialog.py",
    "credentials.py",
    "auth_client.py",
    "hub.env.default",
)

SCAN_DIRS = ("app", "desktop", "scripts")
SKIP_PATH_PARTS = (
    "__pycache__",
    ".pyc",
    "bot_engine.py",  # copia storica bot — non bloccare su pattern legacy
    "node_modules",
    "dist",
    "build",
)
