from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ProductImportError, ProductNotFoundError
from app.core.logging import get_logger
from app.ingestion.product_excel_loader import parse_products_excel
from app.models.product import Product
from app.repositories.product_repo import ProductRepository, ProductSearchHit
from app.schemas.product import ProductImportResult

logger = get_logger(__name__)


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    def get_by_internal_code(self, internal_code: str) -> Product:
        product = self.repository.get_by_internal_code(internal_code)
        if not product:
            raise ProductNotFoundError(
                f"Prodotto con codice '{internal_code}' non trovato"
            )
        return product

    def list_products(
        self,
        *,
        category: str | None = None,
        manufacturer: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        return self.repository.list_products(
            category=category,
            manufacturer=manufacturer,
            limit=limit,
            offset=offset,
        )

    def search_products(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductSearchHit], int]:
        return self.repository.search_fulltext(
            query=query,
            limit=limit,
            offset=offset,
        )

    def create_product(self, data: dict) -> Product:
        if self.repository.get_by_internal_code(data["internal_code"]):
            raise ProductImportError(
                f"Codice interno già presente: {data['internal_code']}"
            )
        product = self.repository.create_product(data)
        self.session.commit()
        logger.info("Prodotto creato: %s", product.internal_code)
        return product

    def update_product(self, internal_code: str, data: dict) -> Product:
        product = self.get_by_internal_code(internal_code)
        updated = self.repository.update_product(product, data)
        self.session.commit()
        logger.info("Prodotto aggiornato: %s", updated.internal_code)
        return updated

    def import_from_excel(
        self,
        source: Path | BytesIO,
    ) -> ProductImportResult:
        rows, parse_errors = parse_products_excel(source)

        imported = 0
        updated = 0
        skipped = 0
        errors = list(parse_errors)

        for row in rows:
            try:
                _, created = self.repository.upsert_product(**row)
                if created:
                    imported += 1
                else:
                    updated += 1
            except Exception as exc:
                skipped += 1
                message = (
                    f"Codice {row.get('internal_code', '?')}: "
                    f"importazione fallita ({exc})"
                )
                logger.error(message)
                errors.append(message)

        self.session.commit()
        logger.info(
            "Import Excel completato: importati=%d, aggiornati=%d, saltati=%d",
            imported,
            updated,
            skipped,
        )

        return ProductImportResult(
            total_rows=len(rows) + len(parse_errors),
            imported=imported,
            updated=updated,
            skipped=skipped + len(parse_errors),
            errors=errors,
        )
