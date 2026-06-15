from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger
from app.integrations.easyone.endpoints import EasyOneEndpoints
from app.integrations.easyone.http_client import EasyOneHttpClient, get_erp_client
from app.integrations.easyone.response_utils import extract_easyone_items, macsystem_list_params
from app.schemas.chat import AvailabilityInfo
from app.schemas.product import ProductResponse
from app.schemas.warehouse import WarehouseItem
from app.utils.availability import availability_info

logger = get_logger(__name__)


class EasyOneStockClient:
    """Client ERP per giacenze live."""

    def __init__(self, http_client: EasyOneHttpClient | None = None) -> None:
        self.http = http_client or get_erp_client()
        self.endpoints = EasyOneEndpoints.from_settings(self.http.settings)

    def get_stock(self, internal_code: str) -> WarehouseItem | None:
        path = self.endpoints.stock_by_code.format(code=internal_code)
        try:
            data = self.http.get(path)
        except Exception as exc:
            logger.warning("ERP stock %s non disponibile: %s", internal_code, exc)
            return None
        if not data or not isinstance(data, dict):
            return None
        return self._parse_stock(data, internal_code)

    def list_stock(self, *, take: int = 100, skip: int = 0) -> list[WarehouseItem]:
        try:
            data = self.http.get(
                self.endpoints.stock_search,
                params=macsystem_list_params(take=take, skip=skip),
            )
        except Exception as exc:
            logger.warning("ERP stock list non disponibile: %s", exc)
            return []

        results: list[WarehouseItem] = []
        for item in extract_easyone_items(data):
            code = item.get("internal_code") or item.get("code") or item.get("articleCode")
            if code:
                parsed = self._parse_stock(item, str(code))
                if parsed:
                    results.append(parsed)
        return results

    def search(self, query: str, *, limit: int = 20) -> list[WarehouseItem]:
        params = macsystem_list_params(take=limit, skip=0, search_value=query)
        params.update({"q": query, "limit": limit})
        try:
            data = self.http.get(self.endpoints.stock_search, params=params)
        except Exception as exc:
            logger.warning("ERP stock search non disponibile: %s", exc)
            return []

        items = extract_easyone_items(data)
        results: list[WarehouseItem] = []
        for item in items[:limit]:
            code = item.get("internal_code") or item.get("code") if isinstance(item, dict) else None
            if code:
                parsed = self._parse_stock(item, str(code))
                if parsed:
                    results.append(parsed)
        return results

    def _parse_stock(self, data: dict[str, Any], internal_code: str) -> WarehouseItem | None:
        now = datetime.now(UTC)
        qty = int(data.get("availability") or data.get("quantity") or data.get("stock") or 0)
        product_data = data.get("product") if isinstance(data.get("product"), dict) else data
        try:
            product = ProductResponse(
                id=product_data.get("id") or uuid4(),
                internal_code=str(product_data.get("internal_code") or internal_code),
                manufacturer=str(product_data.get("manufacturer") or product_data.get("brand") or ""),
                description=str(product_data.get("description") or product_data.get("name") or ""),
                category=str(product_data.get("category") or ""),
                availability=qty,
                price=Decimal(str(product_data.get("price") or "0")),
                created_at=now,
                updated_at=now,
            )
        except Exception as exc:
            logger.warning("Parsing stock ERP fallito: %s", exc)
            return None

        return WarehouseItem(
            product=product,
            availability=availability_info(product),
            warehouse_code=str(data.get("warehouse_code") or "MAIN"),
            location=data.get("location") or data.get("ubicazione"),
            fetched_at=now,
            source="erp_http",
        )
