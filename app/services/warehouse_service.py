from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.integrations.easyone.context import build_erp_client
from app.integrations.easyone.factory import get_easyone_adapter
from app.integrations.easyone.stock_client import EasyOneStockClient
from app.schemas.product import ProductResponse
from app.schemas.warehouse import WarehouseItem, WarehouseSearchResponse
from app.services.product_service import ProductService
from app.utils.availability import availability_info


class WarehouseService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.product_service = ProductService(session)
        self.easyone = get_easyone_adapter(session, self.settings)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        easyone_access_token: str | None = None,
    ) -> WarehouseSearchResponse:
        erp = build_erp_client(self.settings, access_token=easyone_access_token)
        if erp:
            stock_client = EasyOneStockClient(erp)
            remote = stock_client.search(query, limit=limit)
            if remote:
                return WarehouseSearchResponse(items=remote, total=len(remote))

        hits, total = self.product_service.search_products(query, limit=limit, offset=0)
        now = datetime.now(UTC)
        items: list[WarehouseItem] = []

        for hit in hits:
            product = hit.product
            try:
                bundle = self.easyone.get_product_by_code(product.internal_code)
                items.append(
                    WarehouseItem(
                        product=bundle.product,
                        availability=bundle.availability,
                        fetched_at=now,
                        source=bundle.source,
                    )
                )
            except Exception:
                product_response = ProductResponse.model_validate(product)
                items.append(
                    WarehouseItem(
                        product=product_response,
                        availability=availability_info(product_response),
                        fetched_at=now,
                        source="local",
                    )
                )

        return WarehouseSearchResponse(items=items, total=total)

    def get_stock(
        self,
        internal_code: str,
        *,
        easyone_access_token: str | None = None,
    ) -> WarehouseItem | None:
        erp = build_erp_client(self.settings, access_token=easyone_access_token)
        if erp:
            stock_client = EasyOneStockClient(erp)
            remote = stock_client.get_stock(internal_code)
            if remote:
                return remote

        try:
            bundle = self.easyone.get_product_by_code(internal_code)
            return WarehouseItem(
                product=bundle.product,
                availability=bundle.availability,
                fetched_at=datetime.now(UTC),
                source=bundle.source,
            )
        except Exception:
            product = self.product_service.repository.get_by_internal_code(internal_code)
            if not product:
                return None
            product_response = ProductResponse.model_validate(product)
            return WarehouseItem(
                product=product_response,
                availability=availability_info(product_response),
                fetched_at=datetime.now(UTC),
                source="local",
            )
