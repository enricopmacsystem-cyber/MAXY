from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CompatibilityError
from app.core.logging import get_logger
from app.models.compatibility import CompatibilityType, ProductCompatibility
from app.models.product import Product

logger = get_logger(__name__)

TYPE_FIELD_MAP: dict[str, str] = {
    CompatibilityType.ACCESSORY.value: "accessories",
    CompatibilityType.ALTERNATIVE.value: "alternatives",
    CompatibilityType.SPARE_PART.value: "spare_parts",
    CompatibilityType.COMPLEMENTARY.value: "complementary",
}


@dataclass
class RelatedProductEntry:
    product: Product
    notes: str | None
    sort_order: int


@dataclass
class CompatibilityGroups:
    accessories: list[RelatedProductEntry] = field(default_factory=list)
    alternatives: list[RelatedProductEntry] = field(default_factory=list)
    spare_parts: list[RelatedProductEntry] = field(default_factory=list)
    complementary: list[RelatedProductEntry] = field(default_factory=list)


class CompatibilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_link(
        self,
        *,
        product_id: UUID,
        related_product_id: UUID,
        compatibility_type: CompatibilityType,
        notes: str | None = None,
        sort_order: int = 0,
    ) -> ProductCompatibility:
        if product_id == related_product_id:
            raise CompatibilityError("Un prodotto non può essere compatibile con se stesso")

        existing = self.session.scalar(
            select(ProductCompatibility).where(
                ProductCompatibility.product_id == product_id,
                ProductCompatibility.related_product_id == related_product_id,
                ProductCompatibility.compatibility_type == compatibility_type.value,
            )
        )
        if existing:
            raise CompatibilityError(
                "Esiste già un collegamento con lo stesso tipo di compatibilità"
            )

        link = ProductCompatibility(
            product_id=product_id,
            related_product_id=related_product_id,
            compatibility_type=compatibility_type.value,
            notes=notes,
            sort_order=sort_order,
        )
        self.session.add(link)
        self.session.flush()
        logger.info(
            "Creato collegamento compatibilità %s -> %s (%s)",
            product_id,
            related_product_id,
            compatibility_type.value,
        )
        return link

    def get_grouped_for_products(
        self,
        product_ids: list[UUID],
    ) -> dict[UUID, CompatibilityGroups]:
        if not product_ids:
            return {}

        stmt = (
            select(ProductCompatibility, Product)
            .join(Product, ProductCompatibility.related_product_id == Product.id)
            .where(ProductCompatibility.product_id.in_(product_ids))
            .order_by(
                ProductCompatibility.sort_order.asc(),
                Product.internal_code.asc(),
            )
        )
        rows = self.session.execute(stmt).all()

        grouped: dict[UUID, CompatibilityGroups] = {
            product_id: CompatibilityGroups() for product_id in product_ids
        }

        for link, related_product in rows:
            entry = RelatedProductEntry(
                product=related_product,
                notes=link.notes,
                sort_order=link.sort_order,
            )
            bundle = grouped.setdefault(link.product_id, CompatibilityGroups())
            field_name = TYPE_FIELD_MAP.get(link.compatibility_type)
            if not field_name:
                logger.warning("Tipo compatibilità sconosciuto: %s", link.compatibility_type)
                continue
            getattr(bundle, field_name).append(entry)

        logger.debug(
            "Caricate compatibilità per %d prodotti (%d collegamenti)",
            len(product_ids),
            len(rows),
        )
        return grouped
