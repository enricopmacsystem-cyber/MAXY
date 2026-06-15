#!/usr/bin/env python3
"""ETL storico ordini: import Excel + calcolo raccomandazioni."""

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
from app.services.recommendation_service import RecommendationService

logger = get_logger(__name__)

SAMPLE_ORDER_ROWS = [
    [
        "numero_ordine",
        "data_ordine",
        "codice_cliente",
        "codice_interno",
        "quantita",
        "prezzo_unitario",
    ],
    ["ORD-1001", "2025-01-10", "CLI-001", "RT-AX58U", 2, 129.90],
    ["ORD-1001", "2025-01-10", "CLI-001", "HDMI-2M-4K", 4, 9.50],
    ["ORD-1001", "2025-01-10", "CLI-001", "SW-24G-PoE", 1, 349.00],
    ["ORD-1002", "2025-01-12", "CLI-002", "RT-AX58U", 1, 129.90],
    ["ORD-1002", "2025-01-12", "CLI-002", "HDMI-2M-4K", 2, 9.50],
    ["ORD-1003", "2025-01-15", "CLI-003", "RT-AX58U", 3, 129.90],
    ["ORD-1003", "2025-01-15", "CLI-003", "RT-AX58U-PSU", 3, 24.90],
    ["ORD-1004", "2025-01-18", "CLI-001", "SW-24G-PoE", 2, 349.00],
    ["ORD-1004", "2025-01-18", "CLI-001", "HDMI-2M-4K", 6, 9.50],
    ["ORD-1005", "2025-01-20", "CLI-004", "RT-AX86U", 1, 189.00],
    ["ORD-1005", "2025-01-20", "CLI-004", "HDMI-2M-4K", 1, 9.50],
    ["ORD-1006", "2025-01-22", "CLI-002", "RT-AX58U", 2, 129.90],
    ["ORD-1006", "2025-01-22", "CLI-002", "SW-24G-PoE", 1, 349.00],
    ["ORD-1006", "2025-01-22", "CLI-002", "RT-AX58U-PSU", 2, 24.90],
    ["ORD-1007", "2025-01-25", "CLI-005", "RT-AX58U", 1, 129.90],
    ["ORD-1007", "2025-01-25", "CLI-005", "HDMI-2M-4K", 3, 9.50],
    ["ORD-1008", "2025-01-28", "CLI-003", "RT-AX58U", 1, 129.90],
    ["ORD-1008", "2025-01-28", "CLI-003", "HDMI-2M-4K", 2, 9.50],
    ["ORD-1008", "2025-01-28", "CLI-003", "RT-AX58U-PSU", 1, 24.90],
]


def generate_sample_excel(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ordini"
    for row in SAMPLE_ORDER_ROWS:
        sheet.append(row)
    workbook.save(output_path)
    logger.info("File Excel ordini di esempio creato: %s", output_path)


def run_etl(file_path: Path, recompute: bool) -> None:
    session = get_session_factory()()
    try:
        service = RecommendationService(session)
        result = service.import_orders_from_excel(file_path, recompute=recompute)
    finally:
        session.close()

    print("ETL ordini completato")
    print(f"  Ordini importati:  {result.orders_imported}")
    print(f"  Ordini aggiornati: {result.orders_updated}")
    print(f"  Righe importate:   {result.lines_imported}")
    print(f"  Righe saltate:     {result.lines_skipped}")
    print(f"  Coppie calcolate:  {result.recommendations_computed}")
    if result.errors:
        print("\nErrori:")
        for error in result.errors:
            print(f"  - {error}")


def recompute_only() -> None:
    session = get_session_factory()()
    try:
        service = RecommendationService(session)
        result = service.recompute_recommendations()
    finally:
        session.close()

    print("Ricalcolo raccomandazioni completato")
    print(f"  Prodotti con stats: {result.products_with_stats}")
    print(f"  Coppie correlazione: {result.cooccurrence_pairs}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL storico ordini e raccomandazioni")
    parser.add_argument(
        "excel_file",
        nargs="?",
        type=Path,
        help="Percorso file Excel ordini (.xlsx)",
    )
    parser.add_argument(
        "--generate-sample",
        type=Path,
        metavar="OUTPUT",
        help="Genera file Excel di esempio",
    )
    parser.add_argument(
        "--recompute-only",
        action="store_true",
        help="Ricalcola solo le raccomandazioni senza import",
    )
    parser.add_argument(
        "--no-recompute",
        action="store_true",
        help="Import senza ricalcolo raccomandazioni",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)

    if args.recompute_only:
        recompute_only()
        return

    if args.generate_sample:
        generate_sample_excel(args.generate_sample)
        if not args.excel_file:
            return

    if not args.excel_file:
        default_sample = PROJECT_ROOT / "data" / "samples" / "ordini_esempio.xlsx"
        if not default_sample.exists():
            generate_sample_excel(default_sample)
        excel_path = default_sample
        logger.info("Nessun file specificato, uso sample: %s", excel_path)
    else:
        excel_path = args.excel_file

    run_etl(excel_path, recompute=not args.no_recompute)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error("ETL ordini fallito: %s", exc)
        raise SystemExit(1) from exc
