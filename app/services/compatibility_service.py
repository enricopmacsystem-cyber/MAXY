from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import CompatibilityError, ProductNotFoundError
from app.core.logging import get_logger
from app.models.compatibility import CompatibilityType
from app.models.product import Product
from app.repositories.compatibility_repo import (
    CompatibilityGroups,
    CompatibilityRepository,
    RelatedProductEntry,
)
from app.repositories.product_repo import ProductRepository
from app.schemas.compatibility import (
    CompatibilityLinkResponse,
    ProductCompatibilityBundle,
    RelatedProductResponse,
)
from app.schemas.product import ProductResponse

logger = get_logger(__name__)


class CompatibilityService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = CompatibilityRepository(session)
        self.product_repository = ProductRepository(session)

    def get_bundle_for_product(self, product: Product) -> ProductCompatibilityBundle:
        grouped = self.repository.get_grouped_for_products([product.id])
        return self._to_bundle(grouped.get(product.id, CompatibilityGroups()))

    def get_bundles_for_products(
        self,
        products: list[Product],
    ) -> dict[UUID, ProductCompatibilityBundle]:
        product_ids = [product.id for product in products]
        grouped = self.repository.get_grouped_for_products(product_ids)
        return {
            product.id: self._to_bundle(grouped.get(product.id, CompatibilityGroups()))
            for product in products
        }

    def add_compatibility_link(
        self,
        product_code: str,
        related_code: str,
        compatibility_type: CompatibilityType,
        notes: str | None = None,
        sort_order: int = 0,
    ) -> CompatibilityLinkResponse:
        product = self.product_repository.get_by_internal_code(product_code)
        related = self.product_repository.get_by_internal_code(related_code)

        if not product:
            raise ProductNotFoundError(f"Prodotto '{product_code}' non trovato")
        if not related:
            raise ProductNotFoundError(f"Prodotto correlato '{related_code}' non trovato")

        try:
            link = self.repository.add_link(
                product_id=product.id,
                related_product_id=related.id,
                compatibility_type=compatibility_type,
                notes=notes,
                sort_order=sort_order,
            )
        except CompatibilityError:
            raise
        except Exception as exc:
            raise CompatibilityError(f"Impossibile creare il collegamento: {exc}") from exc

        self.session.commit()
        return CompatibilityLinkResponse(
            id=str(link.id),
            product_code=product.internal_code,
            related_product_code=related.internal_code,
            compatibility_type=compatibility_type,
            notes=link.notes,
            sort_order=link.sort_order,
        )

    @staticmethod
    def _to_related_response(entry: RelatedProductEntry) -> RelatedProductResponse:
        return RelatedProductResponse(
            product=ProductResponse.model_validate(entry.product),
            notes=entry.notes,
            sort_order=entry.sort_order,
        )

    def _to_bundle(self, groups: CompatibilityGroups) -> ProductCompatibilityBundle:
        return ProductCompatibilityBundle(
            accessories=[self._to_related_response(item) for item in groups.accessories],
            alternatives=[self._to_related_response(item) for item in groups.alternatives],
            spare_parts=[self._to_related_response(item) for item in groups.spare_parts],
            complementary=[
                self._to_related_response(item) for item in groups.complementary
            ],
        )
