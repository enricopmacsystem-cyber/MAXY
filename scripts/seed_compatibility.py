#!/usr/bin/env python3
"""Popola collegamenti di compatibilità di esempio."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import get_session_factory
from app.models.compatibility import CompatibilityType
from app.services.compatibility_service import CompatibilityService

logger = get_logger(__name__)

SAMPLE_LINKS = [
    ("RT-AX58U", "HDMI-2M-4K", CompatibilityType.ACCESSORY, "Cavo HDMI consigliato"),
    ("RT-AX58U", "RT-AX86U", CompatibilityType.ALTERNATIVE, "Router equivalente di fascia superiore"),
    ("RT-AX58U", "RT-AX58U-PSU", CompatibilityType.SPARE_PART, "Alimentatore originale"),
    ("RT-AX58U", "SW-24G-PoE", CompatibilityType.COMPLEMENTARY, "Switch per rete magazzino"),
    ("SW-24G-PoE", "HDMI-2M-4K", CompatibilityType.ACCESSORY, "Cavo per monitor rack"),
]


def seed_compatibility() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    session = get_session_factory()()
    service = CompatibilityService(session)

    created = 0
    skipped = 0

    for product_code, related_code, link_type, notes in SAMPLE_LINKS:
        try:
            service.add_compatibility_link(
                product_code=product_code,
                related_code=related_code,
                compatibility_type=link_type,
                notes=notes,
            )
            created += 1
        except Exception as exc:
            skipped += 1
            logger.warning(
                "Saltato %s -> %s (%s): %s",
                product_code,
                related_code,
                link_type.value,
                exc,
            )

    logger.info("Seed compatibilità completato: creati=%d, saltati=%d", created, skipped)
    print(f"Collegamenti creati: {created}")
    print(f"Collegamenti saltati: {skipped}")


if __name__ == "__main__":
    try:
        seed_compatibility()
    except Exception as exc:
        logger.error("Seed compatibilità fallito: %s", exc)
        raise SystemExit(1) from exc
