from __future__ import annotations

import json
import os
import sys
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HUB_BASE_URL = "http://127.0.0.1:8000"


def get_app_data_dir() -> Path:
    """Directory dati utente: %APPDATA%\\MAC AI Assistant"""
    appdata = os.getenv("APPDATA")
    if appdata:
        path = Path(appdata) / "MAC AI Assistant"
    else:
        path = Path.home() / "AppData" / "Roaming" / "MAC AI Assistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_app_data_dir() / "config.ini"


def get_install_dir() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None


def _load_version_from_bundle() -> str:
    install = get_install_dir()
    if install:
        version_file = install / "version.json"
        if not version_file.exists():
            version_file = install / "_internal" / "version.json"
        if version_file.exists():
            try:
                data = json.loads(version_file.read_text(encoding="utf-8"))
                return str(data.get("version", "2.0"))
            except Exception:
                pass
    return "2.0"


@dataclass(frozen=True)
class AppConfig:
    hub_base_url: str
    app_version: str
    auth_required: bool = True
    first_run: bool = False
    config_path: Path | None = None

    @classmethod
    def load(cls) -> "AppConfig":
        hub_url = os.getenv("HUB_BASE_URL", "").strip()
        version = os.getenv("APP_VERSION", "").strip() or _load_version_from_bundle()
        auth_required = True
        if os.getenv("AUTH_REQUIRED", "").lower() == "false":
            auth_required = False

        config_path = get_config_path()
        if not config_path.exists():
            return cls.save(
                hub_base_url=hub_url or DEFAULT_HUB_BASE_URL,
                app_version=version,
                auth_required=True,
                first_run=False,
            )

        parser = ConfigParser()
        parser.read(config_path, encoding="utf-8")
        if parser.has_option("hub", "base_url") and not hub_url:
            hub_url = parser.get("hub", "base_url").strip()
        if parser.has_option("app", "version") and not version:
            version = parser.get("app", "version").strip()
        if parser.has_option("hub", "auth_required"):
            auth_required = parser.getboolean("hub", "auth_required", fallback=True)

        hub_url = (hub_url or DEFAULT_HUB_BASE_URL).rstrip("/")
        version = version or "2.0"

        needs_migration = False
        if parser.has_option("app", "first_run") and parser.getboolean(
            "app", "first_run", fallback=False
        ):
            needs_migration = True
        if parser.has_option("hub", "auth_required") and not parser.getboolean(
            "hub", "auth_required", fallback=True
        ):
            needs_migration = True
        if needs_migration:
            return cls.save(
                hub_base_url=hub_url,
                app_version=version,
                auth_required=True,
                first_run=False,
            )

        return cls(
            hub_base_url=hub_url,
            app_version=version,
            auth_required=auth_required,
            first_run=False,
            config_path=config_path,
        )

    @classmethod
    def save(
        cls,
        *,
        hub_base_url: str,
        app_version: str | None = None,
        auth_required: bool = True,
        first_run: bool = False,
    ) -> "AppConfig":
        config_path = get_config_path()
        parser = ConfigParser()
        if config_path.exists():
            parser.read(config_path, encoding="utf-8")
        if not parser.has_section("hub"):
            parser.add_section("hub")
        if not parser.has_section("app"):
            parser.add_section("app")

        parser.set("hub", "base_url", hub_base_url.rstrip("/"))
        parser.set("hub", "auth_required", "true" if auth_required else "false")
        parser.set("app", "version", app_version or _load_version_from_bundle())
        parser.set("app", "first_run", "false" if not first_run else "true")

        with config_path.open("w", encoding="utf-8") as fh:
            parser.write(fh)

        return cls.load()

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls.load()
