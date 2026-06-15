from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.product import Product

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProductSearchHit:
    product: Product
    rank: float


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_internal_code(self, internal_code: str) -> Product | None:
        stmt = select(Product).where(Product.internal_code == internal_code.strip())
        return self.session.scalar(stmt)

    def list_products(
        self,
        *,
        category: str | None = None,
        manufacturer: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        filters = []
        if category:
            filters.append(Product.category.ilike(f"%{category.strip()}%"))
        if manufacturer:
            filters.append(Product.manufacturer.ilike(f"%{manufacturer.strip()}%"))

        count_stmt = select(func.count()).select_from(Product)
        list_stmt = select(Product).order_by(Product.internal_code.asc())

        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = self.session.scalar(count_stmt) or 0
        products = list(
            self.session.scalars(
                list_stmt.limit(limit).offset(offset)
            ).all()
        )
        return products, int(total)

    def search_fulltext(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductSearchHit], int]:
        cleaned = query.strip()
        if not cleaned:
            return [], 0

        ts_query = func.plainto_tsquery("italian", cleaned)
        rank_expr = func.ts_rank(Product.search_vector, ts_query)

        filters = or_(
            Product.search_vector.op("@@")(ts_query),
            Product.internal_code.ilike(f"%{cleaned}%"),
            Product.description.ilike(f"%{cleaned}%"),
            Product.manufacturer.ilike(f"%{cleaned}%"),
        )

        count_stmt = select(func.count()).select_from(Product).where(filters)
        list_stmt = (
            select(Product, rank_expr.label("rank"))
            .where(filters)
            .order_by(rank_expr.desc(), Product.internal_code.asc())
            .limit(limit)
            .offset(offset)
        )

        total = self.session.scalar(count_stmt) or 0
        rows = self.session.execute(list_stmt).all()

        hits = [
            ProductSearchHit(product=row[0], rank=float(row[1] or 0.0))
            for row in rows
        ]

        logger.info(
            "Full-text search '%s': %d risultati (totale=%d)",
            cleaned,
            len(hits),
            total,
        )
        return hits, int(total)

    def upsert_product(
        self,
        *,
        internal_code: str,
        manufacturer: str,
        description: str,
        category: str,
        availability: int,
        price: Decimal,
        manual_url: str | None,
        datasheet_url: str | None,
        cost_price: Decimal | None = None,
    ) -> tuple[Product, bool]:
        existing = self.get_by_internal_code(internal_code)
        if existing:
            existing.manufacturer = manufacturer
            existing.description = description
            existing.category = category
            existing.availability = availability
            existing.price = price
            existing.cost_price = cost_price
            existing.manual_url = manual_url
            existing.datasheet_url = datasheet_url
            self.session.flush()
            return existing, False

        product = Product(
            internal_code=internal_code,
            manufacturer=manufacturer,
            description=description,
            category=category,
            availability=availability,
            price=price,
            cost_price=cost_price,
            manual_url=manual_url,
            datasheet_url=datasheet_url,
        )
        self.session.add(product)
        self.session.flush()
        return product, True

    def create_product(self, data: dict) -> Product:
        product = Product(**data)
        self.session.add(product)
        self.session.flush()
        return product

    def update_product(self, product: Product, data: dict) -> Product:
        for key, value in data.items():
            if value is not None:
                setattr(product, key, value)
        self.session.flush()
        return product

    def delete_product(self, product: Product) -> None:
        self.session.delete(product)
        self.session.flush()

    def find_similar_products(
        self,
        product: Product,
        *,
        limit: int = 5,
    ) -> list[Product]:
        """Prodotti simili: stessa categoria, escluso se stesso, ordinati per marca/descrizione."""
        stmt = (
            select(Product)
            .where(
                Product.category == product.category,
                Product.id != product.id,
                Product.availability >= 0,
            )
            .order_by(
                Product.manufacturer.asc(),
                Product.description.asc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def find_higher_margin_products(
        self,
        product: Product,
        *,
        anchor_margin: Decimal | None,
        limit: int = 5,
    ) -> list[Product]:
        """
        Prodotti nella stessa categoria con margine superiore all'articolo richiesto.
        """
        from app.utils.margin import calculate_margin_percent

        anchor = anchor_margin
        if anchor is None:
            anchor = calculate_margin_percent(product.price, product.cost_price)

        stmt = (
            select(Product)
            .where(
                Product.category == product.category,
                Product.id != product.id,
            )
            .order_by(Product.price.desc())
            .limit(limit * 3)
        )
        candidates = list(self.session.scalars(stmt).all())

        if anchor is None:
            return [p for p in candidates if p.price > product.price][:limit]

        results: list[Product] = []
        for candidate in candidates:
            candidate_margin = calculate_margin_percent(
                candidate.price,
                candidate.cost_price,
            )
            if candidate_margin is not None and candidate_margin > anchor:
                results.append(candidate)
            if len(results) >= limit:
                break
        return results
