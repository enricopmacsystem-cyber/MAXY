from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import OrderImportError, ProductNotFoundError
from app.core.logging import get_logger
from app.ingestion.order_excel_loader import parse_orders_excel
from app.repositories.order_repo import OrderRepository, RecommendationRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.product import ProductResponse
from app.schemas.recommendation import (
    BoughtTogetherItem,
    ProductRecommendationResponse,
    PurchaseFrequency,
    RecommendationImportResult,
    RecomputeResult,
)

logger = get_logger(__name__)


class RecommendationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.order_repository = OrderRepository(session)
        self.recommendation_repository = RecommendationRepository(session)
        self.product_repository = ProductRepository(session)

    def get_recommendations_for_product(
        self,
        internal_code: str,
        *,
        limit: int = 10,
    ) -> ProductRecommendationResponse:
        product = self.product_repository.get_by_internal_code(internal_code)
        if not product:
            raise ProductNotFoundError(
                f"Prodotto con codice '{internal_code}' non trovato"
            )

        stats = self.recommendation_repository.get_stats(product.id)
        hits = self.recommendation_repository.get_recommendations(
            product.id,
            limit=limit,
        )

        if stats:
            frequency = PurchaseFrequency(
                order_count=stats.order_count,
                line_count=stats.line_count,
                total_quantity=stats.total_quantity,
            )
        else:
            frequency = PurchaseFrequency(
                order_count=0,
                line_count=0,
                total_quantity=0,
            )

        bought_together = [
            BoughtTogetherItem(
                product=ProductResponse.model_validate(hit.related_product),
                cooccurrence_count=hit.cooccurrence_count,
                correlation_percent=hit.correlation_percent,
            )
            for hit in hits
        ]

        logger.info(
            "Raccomandazioni per %s: %d articoli correlati",
            internal_code,
            len(bought_together),
        )

        return ProductRecommendationResponse(
            product=ProductResponse.model_validate(product),
            purchase_frequency=frequency,
            bought_together=bought_together,
        )

    def import_orders_from_excel(
        self,
        source: Path | BytesIO,
        *,
        recompute: bool = True,
    ) -> RecommendationImportResult:
        rows, parse_errors = parse_orders_excel(source)

        orders_imported = 0
        orders_updated = 0
        lines_imported = 0
        lines_skipped = 0
        errors = list(parse_errors)
        created_orders: set[str] = set()
        updated_orders: set[str] = set()

        for row in rows:
            product = self.product_repository.get_by_internal_code(row.internal_code)
            if not product:
                lines_skipped += 1
                message = (
                    f"Ordine {row.order_number}: prodotto '{row.internal_code}' "
                    "non trovato nel catalogo"
                )
                logger.warning(message)
                errors.append(message)
                continue

            try:
                order, order_created = self.order_repository.upsert_order(
                    order_number=row.order_number,
                    order_date=row.order_date,
                    customer_code=row.customer_code,
                )
                if order_created:
                    if row.order_number not in created_orders:
                        orders_imported += 1
                        created_orders.add(row.order_number)
                elif row.order_number not in created_orders and row.order_number not in updated_orders:
                    orders_updated += 1
                    updated_orders.add(row.order_number)

                _, line_created = self.order_repository.upsert_order_line(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=row.quantity,
                    unit_price=row.unit_price,
                )
                if line_created:
                    lines_imported += 1
            except Exception as exc:
                lines_skipped += 1
                message = f"Ordine {row.order_number}: import fallito ({exc})"
                logger.error(message)
                errors.append(message)

        recommendations_computed = 0
        if recompute:
            _, pairs = self.recommendation_repository.recompute_all()
            recommendations_computed = pairs

        self.session.commit()
        logger.info(
            "Import ordini completato: ordini=%d/%d, righe=%d",
            orders_imported,
            orders_updated,
            lines_imported,
        )

        return RecommendationImportResult(
            orders_imported=orders_imported,
            orders_updated=orders_updated,
            lines_imported=lines_imported,
            lines_skipped=lines_skipped + len(parse_errors),
            recommendations_computed=recommendations_computed,
            errors=errors,
        )

    def recompute_recommendations(self) -> RecomputeResult:
        products, pairs = self.recommendation_repository.recompute_all()
        self.session.commit()
        return RecomputeResult(
            products_with_stats=products,
            cooccurrence_pairs=pairs,
        )
