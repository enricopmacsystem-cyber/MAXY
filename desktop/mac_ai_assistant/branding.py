"""Branding condiviso desktop MAC AI Assistant."""

from __future__ import annotations

import sys
from pathlib import Path

APP_DISPLAY_NAME = "Maxy AI"
APP_VERSION_LABEL = "v.2.0 beta"
APP_VERSION_CODE = "2.0"
BUILD_NAME = "daisy"
DEVELOPER_NAME = "Andrea Santin"
DEVELOPER_EMAIL = "andrea.santin@macsystem.it"
AI_ASSISTANT_NAME = "Maxy"
ORGANIZATION_NAME = "MacSystem s.r.l."


def window_title() -> str:
    return f"{APP_DISPLAY_NAME} {APP_VERSION_LABEL}"


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1] / "resources"


def app_icon_path() -> Path | None:
    resources = resource_dir()
    for name in ("app.ico", "logo-m.png"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def splash_screen_path() -> Path | None:
    """Immagine splash Maxy su sfondo bianco."""
    resources = resource_dir()
    for name in ("splash-maxy.png", "splash-maxy-source.png"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def release_notes_path() -> Path | None:
    """Note di rilascio (funzioni, correzioni, motivazioni)."""
    resources = resource_dir()
    for name in ("release_notes_it.txt", "RELEASE_NOTES.txt"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def company_banner_path() -> Path | None:
    resources = resource_dir()
    for name in ("mac-system-banner.png", "logo-banner.png"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def header_logo_path() -> Path | None:
    """Logo M in alto a sinistra (versione nitida per toolbar)."""
    resources = resource_dir()
    for name in ("logo-m-header.png", "logo-m.png", "app.ico"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


def login_footer_logo_path() -> Path | None:
    resources = resource_dir()
    for name in ("mac-system-login-footer.png", "mac-system-banner.png", "logo-banner.png"):
        candidate = resources / name
        if candidate.is_file():
            return candidate
    return None


MACSYSTEM_HOMEPAGE_URL = "https://www.macsystem.it/homepage"
CONNECT_EXE_NAME = "macsystemconnect.exe"
ANDROID_APK_NAME = "MacSystem-2.0.1-Dandelion.apk"
CONNECT_DESKTOP_FILENAME = "MacSystem Connect.exe"
ANDROID_DESKTOP_FILENAME = "MacSystem-2.0.1-Dandelion.apk"


def software_resource_dir() -> Path:
    return resource_dir() / "software"


def bundled_software_path(filename: str) -> Path | None:
    """File software incluso nel bundle (Connect, APK Android, ecc.)."""
    candidate = software_resource_dir() / filename
    if candidate.is_file():
        return candidate
    return None
