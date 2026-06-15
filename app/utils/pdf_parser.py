from dataclasses import dataclass
from pathlib import Path

import fitz

from app.core.exceptions import PDFExtractionError
from app.core.logging import get_logger
from app.utils.text_cleaner import clean_text

logger = get_logger(__name__)


@dataclass(frozen=True)
class PDFPage:
    page_number: int
    content: str


def extract_text_from_pdf(pdf_path: Path) -> list[PDFPage]:
    """
    Estrae il testo da ogni pagina di un file PDF.

    Raises:
        PDFExtractionError: se il file non esiste, è corrotto o non contiene testo.
    """
    if not pdf_path.exists():
        raise PDFExtractionError(f"File PDF non trovato: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise PDFExtractionError(f"Il file non è un PDF: {pdf_path}")

    logger.info("Estrazione testo da PDF: %s", pdf_path.name)

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise PDFExtractionError(
            f"Impossibile aprire il PDF '{pdf_path.name}': {exc}"
        ) from exc

    pages: list[PDFPage] = []

    try:
        for index in range(document.page_count):
            page_number = index + 1
            try:
                page = document.load_page(index)
                raw_text = page.get_text("text")
                content = clean_text(raw_text)

                if content:
                    pages.append(PDFPage(page_number=page_number, content=content))
                    logger.debug(
                        "Pagina %d estratta (%d caratteri) da %s",
                        page_number,
                        len(content),
                        pdf_path.name,
                    )
                else:
                    logger.warning(
                        "Pagina %d vuota o senza testo in %s",
                        page_number,
                        pdf_path.name,
                    )
            except Exception as exc:
                logger.error(
                    "Errore estrazione pagina %d di %s: %s",
                    page_number,
                    pdf_path.name,
                    exc,
                )
    finally:
        document.close()

    if not pages:
        raise PDFExtractionError(
            f"Nessun testo estraibile dal PDF '{pdf_path.name}'"
        )

    logger.info(
        "Estratte %d pagine con testo da %s (totale pagine file: %d)",
        len(pages),
        pdf_path.name,
        page_number if "page_number" in locals() else 0,
    )
    return pages
