#!/usr/bin/env python3
"""Importa prodotti da un file Excel nel database PostgreSQL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from openpyxl import Workbook

from app.config.settings import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import get_session_factory
from app.services.product_service import ProductService

logger = get_logger(__name__)

SAMPLE_ROWS = [
    [
        "codice_interno",
        "produttore",
        "descrizione",
        "categoria",
        "disponibilita",
        "prezzo",
        "costo",
        "link_manuale",
        "link_scheda_tecnica",
    ],
    [
        "RT-AX58U",
        "ASUS",
        "Router Wi-Fi 6 dual band AX5700",
        "Networking",
        24,
        129.90,
        89.00,
        "https://example.com/manuali/rt-ax58u.pdf",
        "https://example.com/schede/rt-ax58u.pdf",
    ],
    [
        "SW-24G-PoE",
        "TP-Link",
        "Switch managed 24 porte Gigabit PoE+",
        "Networking",
        8,
        349.00,
        245.00,
        "https://example.com/manuali/sw-24g-poe.pdf",
        "https://example.com/schede/sw-24g-poe.pdf",
    ],
    [
        "HDMI-2M-4K",
        "TechLine",
        "Cavo HDMI 2.0 da 2 metri supporto 4K",
        "Cavi",
        150,
        9.50,
        4.20,
        "",
        "https://example.com/schede/hdmi-2m-4k.pdf",
    ],
    [
        "RT-AX86U",
        "ASUS",
        "Router Wi-Fi 6 gaming AX5700 alternativo",
        "Networking",
        12,
        189.00,
        132.00,
        "https://example.com/manuali/rt-ax86u.pdf",
        "https://example.com/schede/rt-ax86u.pdf",
    ],
    [
        "RT-AX58U-PSU",
        "ASUS",
        "Alimentatore di ricambio 19V per router RT-AX58U",
        "Ricambi",
        35,
        24.90,
        12.50,
        "",
        "https://example.com/schede/rt-ax58u-psu.pdf",
    ],
]


def generate_sample_excel(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Prodotti"

    for row in SAMPLE_ROWS:
        sheet.append(row)

    workbook.save(output_path)
    logger.info("File Excel di esempio creato: %s", output_path)


def import_excel(file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"File Excel non trovato: {file_path}")

    session = get_session_factory()()
    try:
        service = ProductService(session)
        result = service.import_from_excel(file_path)
    finally:
        session.close()

    print("Import completato")
    print(f"  Righe totali: {result.total_rows}")
    print(f"  Importati:    {result.imported}")
    print(f"  Aggiornati:   {result.updated}")
    print(f"  Saltati:      {result.skipped}")

    if result.errors:
        print("\nErrori:")
        for error in result.errors:
            print(f"  - {error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa prodotti da Excel nel database PostgreSQL"
    )
    parser.add_argument(
        "excel_file",
        nargs="?",
        type=Path,
        help="Percorso del file .xlsx da importare",
    )
    parser.add_argument(
        "--generate-sample",
        type=Path,
        metavar="OUTPUT",
        help="Genera un file Excel di esempio nel percorso indicato",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.generate_sample:
        generate_sample_excel(args.generate_sample)
        if not args.excel_file:
            return

    if not args.excel_file:
        default_sample = PROJECT_ROOT / "data" / "samples" / "prodotti_esempio.xlsx"
        if not default_sample.exists():
            generate_sample_excel(default_sample)
        excel_path = default_sample
        logger.info("Nessun file specificato, uso sample: %s", excel_path)
    else:
        excel_path = args.excel_file

    import_excel(excel_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error("Import prodotti fallito: %s", exc)
        raise SystemExit(1) from exc
