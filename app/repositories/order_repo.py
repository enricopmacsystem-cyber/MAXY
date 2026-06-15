from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.order import Order, OrderLine, ProductCooccurrence, ProductOrderStats
from app.models.product import Product

logger = get_logger(__name__)


@dataclass(frozen=True)
class CooccurrenceHit:
    related_product: Product
    cooccurrence_count: int
    correlation_percent: Decimal


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_order_by_number(self, order_number: str) -> Order | None:
        stmt = select(Order).where(Order.order_number == order_number.strip())
        return self.session.scalar(stmt)

    def upsert_order(
        self,
        *,
        order_number: str,
        order_date: date,
        customer_code: str | None,
    ) -> tuple[Order, bool]:
        existing = self.get_order_by_number(order_number)
        if existing:
            existing.order_date = order_date
            existing.customer_code = customer_code
            self.session.flush()
            return existing, False

        order = Order(
            order_number=order_number,
            order_date=order_date,
            customer_code=customer_code,
        )
        self.session.add(order)
        self.session.flush()
        return order, True

    def upsert_order_line(
        self,
        *,
        order_id: UUID,
        product_id: UUID,
        quantity: Decimal,
        unit_price: Decimal | None,
    ) -> tuple[OrderLine, bool]:
        stmt = select(OrderLine).where(
            OrderLine.order_id == order_id,
            OrderLine.product_id == product_id,
        )
        existing = self.session.scalar(stmt)
        if existing:
            existing.quantity = quantity
            existing.unit_price = unit_price
            self.session.flush()
            return existing, False

        line = OrderLine(
            order_id=order_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.session.add(line)
        self.session.flush()
        return line, True

    def count_customer_orders(self, customer_code: str) -> int:
        normalized = customer_code.strip()
        stmt = select(func.count()).select_from(Order).where(
            func.upper(Order.customer_code) == normalized.upper()
        )
        return int(self.session.scalar(stmt) or 0)

    def get_customer_purchase_aggregates(self, customer_code: str) -> list[dict[str, Any]]:
        normalized = customer_code.strip()
        stmt = (
            select(
                Product,
                func.sum(OrderLine.quantity).label("total_qty"),
                func.count(func.distinct(Order.id)).label("order_count"),
                func.avg(OrderLine.unit_price).label("avg_price"),
            )
            .join(OrderLine, OrderLine.product_id == Product.id)
            .join(Order, Order.id == OrderLine.order_id)
            .where(func.upper(Order.customer_code) == normalized.upper())
            .group_by(Product.id)
            .order_by(func.sum(OrderLine.quantity).desc())
        )
        rows = self.session.execute(stmt).all()
        results: list[dict[str, Any]] = []
        for product, total_qty, order_count, avg_price in rows:
            results.append(
                {
                    "product": product,
                    "total_quantity": Decimal(str(total_qty or 0)),
                    "order_count": int(order_count or 0),
                    "avg_unit_price": (
                        Decimal(str(avg_price)) if avg_price is not None else None
                    ),
                }
            )
        return results


class RecommendationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_stats(self, product_id: UUID) -> ProductOrderStats | None:
        return self.session.get(ProductOrderStats, product_id)

    def get_recommendations(
        self,
        product_id: UUID,
        *,
        limit: int = 10,
    ) -> list[CooccurrenceHit]:
        stmt = (
            select(ProductCooccurrence, Product)
            .join(Product, ProductCooccurrence.related_product_id == Product.id)
            .where(ProductCooccurrence.product_id == product_id)
            .order_by(ProductCooccurrence.correlation_percent.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).all()
        return [
            CooccurrenceHit(
                related_product=product,
                cooccurrence_count=cooccurrence.cooccurrence_count,
                correlation_percent=Decimal(str(cooccurrence.correlation_percent)),
            )
            for cooccurrence, product in rows
        ]

    def recompute_all(self) -> tuple[int, int]:
        """
        Ricalcola statistiche frequenza e co-occorrenze da order_lines.

        Correlazione % = (ordini con A e B) / (ordini con A) * 100
        """
        logger.info("Avvio ricalcolo raccomandazioni da storico ordini")

        self.session.execute(delete(ProductCooccurrence))
        self.session.execute(delete(ProductOrderStats))

        stats_sql = text(
            """
            INSERT INTO product_order_stats (
                product_id, order_count, line_count, total_quantity, computed_at
            )
            SELECT
                ol.product_id,
                COUNT(DISTINCT ol.order_id)::INTEGER,
                COUNT(*)::INTEGER,
                COALESCE(SUM(ol.quantity), 0),
                NOW()
            FROM order_lines ol
            GROUP BY ol.product_id
            """
        )
        self.session.execute(stats_sql)

        cooccurrence_sql = text(
            """
            INSERT INTO product_cooccurrence (
                product_id,
                related_product_id,
                cooccurrence_count,
                correlation_percent,
                computed_at
            )
            SELECT
                pairs.product_id,
                pairs.related_product_id,
                pairs.cooccurrence_count,
                ROUND(
                    pairs.cooccurrence_count * 100.0 / stats.order_count,
                    2
                ) AS correlation_percent,
                NOW()
            FROM (
                SELECT
                    a.product_id,
                    b.product_id AS related_product_id,
                    COUNT(DISTINCT a.order_id)::INTEGER AS cooccurrence_count
                FROM order_lines a
                INNER JOIN order_lines b
                    ON a.order_id = b.order_id
                    AND a.product_id <> b.product_id
                GROUP BY a.product_id, b.product_id
            ) pairs
            INNER JOIN product_order_stats stats
                ON stats.product_id = pairs.product_id
            WHERE stats.order_count > 0
            """
        )
        self.session.execute(cooccurrence_sql)

        products_with_stats = self.session.scalar(
            select(func.count()).select_from(ProductOrderStats)
        ) or 0
        cooccurrence_pairs = self.session.scalar(
            select(func.count()).select_from(ProductCooccurrence)
        ) or 0

        self.session.flush()
        logger.info(
            "Ricalcolo completato: %d prodotti, %d coppie",
            products_with_stats,
            cooccurrence_pairs,
        )
        return int(products_with_stats), int(cooccurrence_pairs)
