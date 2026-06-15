#!/usr/bin/env python3
"""Entry point Integration Hub (sviluppo e build PyInstaller)."""

from __future__ import annotations

# PyInstaller windowed exe: stdout/stderr sono None prima di qualsiasi import.
import os
import sys

if getattr(sys, "frozen", False):
    _stdio_sink = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stdout is None:
        sys.stdout = _stdio_sink
    if sys.stderr is None:
        sys.stderr = _stdio_sink

import argparse
import logging
from pathlib import Path

_EASYONE_KEYS = (
    "EASYONE_API_URL",
    "EASYONE_BASE_URL",
    "EASYONE_EVENTS_URL",
    "EASYONE_EVENTS_BASE_URL",
    "EASYONE_TENANT_ID",
    "EASYONE_PORTAL_URL",
    "EASYONE_CRM_URL",
    "EASYONE_AUTH_MODE",
    "EASYONE_MODE",
    "GEMINI_API_KEY",
    "DATABASE_URL",
)


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def _is_mock_easyone_url(url: str) -> bool:
    lowered = (url or "").lower()
    return "8090" in lowered or "127.0.0.1" in lowered or "localhost" in lowered


def _appdata_hub_env() -> Path | None:
    appdata = os.getenv("APPDATA", "").strip()
    if not appdata:
        return None
    path = Path(appdata) / "MAC AI Assistant" / "hub.env"
    return path if path.is_file() else None


def _hub_log_file() -> Path | None:
    appdata = os.getenv("APPDATA", "").strip()
    if not appdata:
        return None
    log_dir = Path(appdata) / "MAC AI Assistant" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return log_dir / "hub.log"


def _prepare_frozen_stdio() -> None:
    """Exe PyInstaller senza console: uvicorn richiede stdout/stderr validi."""
    if not getattr(sys, "frozen", False):
        return
    log_file = _hub_log_file()
    sink = (
        open(log_file, "a", encoding="utf-8")  # noqa: SIM115
        if log_file
        else open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    )
    if sys.stdout is None:
        sys.stdout = sink
    if sys.stderr is None:
        sys.stderr = sink


def _bootstrap_env() -> None:
    os.environ.setdefault("MAC_AI_PROJECT_ROOT", str(_project_root()))

    try:
        from dotenv import dotenv_values, load_dotenv
    except ImportError:
        return

    for key in ("EASYONE_BASE_URL", "EASYONE_API_URL"):
        if _is_mock_easyone_url(os.environ.get(key, "")):
            os.environ.pop(key, None)

    candidates: list[Path] = []
    override = os.getenv("MAC_AI_HUB_ENV", "").strip()
    if override:
        candidates.append(Path(override))
    appdata_path = _appdata_hub_env()
    if appdata_path:
        candidates.append(appdata_path)
    project_env = _project_root() / ".env"
    if project_env.is_file():
        candidates.append(project_env)

    loaded: Path | None = None
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve())
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        load_dotenv(path, override=True)
        loaded = path
        break

    if loaded:
        os.environ["MAC_AI_HUB_ENV"] = str(loaded)
        file_vals = dotenv_values(loaded)
        api_url = (file_vals.get("EASYONE_API_URL") or file_vals.get("EASYONE_BASE_URL") or "").strip()
        if api_url and "macsystem" in api_url.lower():
            for env_key, val in file_vals.items():
                if env_key in _EASYONE_KEYS and val:
                    os.environ[env_key] = str(val).strip()
            os.environ["EASYONE_API_URL"] = api_url
            os.environ["EASYONE_BASE_URL"] = (file_vals.get("EASYONE_BASE_URL") or api_url).strip()


def _init_database() -> None:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from sqlalchemy import text

    from app.config.settings import get_settings
    from app.core.logging import get_logger, setup_logging
    from app.db.session import get_engine

    get_settings.cache_clear()
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger(__name__)

    schema_path = root / "database" / "schema.sql"
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema SQL non trovato: {schema_path}")

    engine = get_engine()
    logger.info("Inizializzazione database da %s", schema_path)
    with engine.begin() as connection:
        connection.execute(text(schema_path.read_text(encoding="utf-8")))

    migrations_dir = root / "database" / "migrations"
    if migrations_dir.is_dir():
        for migration_path in sorted(migrations_dir.glob("*.sql")):
            logger.info("Migrazione %s", migration_path.name)
            with engine.begin() as connection:
                connection.execute(text(migration_path.read_text(encoding="utf-8")))


def main() -> int:
    _prepare_frozen_stdio()

    parser = argparse.ArgumentParser(description="MAC AI Assistant — Integration Hub")
    parser.add_argument("--init-db", action="store_true", help="Crea/aggiorna schema PostgreSQL")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    _bootstrap_env()

    root = _project_root()
    if not getattr(sys, "frozen", False) and str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if args.init_db:
        _init_database()
        return 0

    log_handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = _hub_log_file()
    if log_file:
        log_handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=log_handlers,
        force=True,
    )

    import uvicorn

    config = uvicorn.Config(
        "app.main:app",
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
