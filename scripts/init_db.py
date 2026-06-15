#!/usr/bin/env python3
"""Applica lo schema PostgreSQL del progetto."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from app.config.settings import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import get_engine

logger = get_logger(__name__)


def init_database() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema SQL non trovato: {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")
    engine = get_engine()

    logger.info("Applicazione schema da %s", schema_path)
    with engine.begin() as connection:
        connection.execute(text(sql))

    migrations_dir = PROJECT_ROOT / "database" / "migrations"
    if migrations_dir.exists():
        migration_files = sorted(migrations_dir.glob("*.sql"))
        for migration_path in migration_files:
            migration_sql = migration_path.read_text(encoding="utf-8")
            logger.info("Applicazione migration %s", migration_path.name)
            with engine.begin() as connection:
                connection.execute(text(migration_sql))

    logger.info("Schema database applicato con successo")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as exc:
        logger.error("Inizializzazione database fallita: %s", exc)
        raise SystemExit(1) from exc
