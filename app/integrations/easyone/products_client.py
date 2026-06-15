from __future__ import annotations



from datetime import UTC, datetime

from decimal import Decimal

from typing import Any

from uuid import uuid4



from app.core.logging import get_logger

from app.integrations.easyone.endpoints import EasyOneEndpoints

from app.integrations.easyone.http_client import EasyOneHttpClient

from app.integrations.easyone.response_utils import extract_easyone_items, macsystem_list_params

from app.schemas.product import ProductResponse



logger = get_logger(__name__)





class EasyOneProductsClient:

    """Recupera articoli da API EasyOne/ERP."""



    def __init__(self, http_client: EasyOneHttpClient | None = None) -> None:

        self.http = http_client or EasyOneHttpClient()

        self.endpoints = EasyOneEndpoints.from_settings(self.http.settings)



    def get_product_by_code(self, internal_code: str) -> ProductResponse | None:

        path = self.endpoints.product_by_code.format(code=internal_code)

        try:

            data = self.http.get(path)

        except Exception as exc:

            logger.warning("EasyOne products API non disponibile: %s", exc)

            return None



        if not data or not isinstance(data, dict):

            return None

        return self._parse_product(data)



    def search_products(self, query: str, *, limit: int = 20) -> list[ProductResponse]:

        params = macsystem_list_params(take=limit, skip=0, search_value=query)

        params.update({"q": query, "limit": limit})

        try:

            data = self.http.get(self.endpoints.products_search, params=params)

        except Exception as exc:

            logger.warning("EasyOne search API non disponibile: %s", exc)

            return []



        items = extract_easyone_items(data)

        results: list[ProductResponse] = []

        for item in items[:limit]:

            parsed = self._parse_product(item)

            if parsed:

                results.append(parsed)

        return results



    def list_products(self, *, take: int = 100, skip: int = 0) -> list[ProductResponse]:

        """Elenco paginato articoli (Mac System: take/skip)."""

        try:

            data = self.http.get(

                self.endpoints.products_search,

                params=macsystem_list_params(take=take, skip=skip),

            )

        except Exception as exc:

            logger.warning("EasyOne list articles non disponibile: %s", exc)

            return []



        results: list[ProductResponse] = []

        for item in extract_easyone_items(data):

            parsed = self._parse_product(item)

            if parsed:

                results.append(parsed)

        return results



    @staticmethod

    def _parse_product(data: dict[str, Any]) -> ProductResponse | None:

        code = (

            data.get("internal_code")

            or data.get("code")

            or data.get("sku")

            or data.get("articleCode")

            or data.get("ArticleCode")

        )

        if not code:

            return None



        stock_block = data.get("inventory") if isinstance(data.get("inventory"), dict) else data

        qty_raw = (

            data.get("availability")

            or data.get("stock")

            or data.get("quantity")

            or stock_block.get("availability")

            or stock_block.get("quantity")

            or stock_block.get("stock")

            or 0

        )



        price_raw = (

            data.get("price")

            or data.get("salePrice")

            or data.get("listPrice")

            or data.get("unitPrice")

            or "0"

        )



        try:

            now = datetime.now(UTC)

            return ProductResponse(

                id=data.get("id") or uuid4(),

                internal_code=str(code),

                manufacturer=str(

                    data.get("manufacturer")

                    or data.get("brand")

                    or data.get("brandDescription")

                    or data.get("manufacturerDescription")

                    or ""

                ),

                description=str(

                    data.get("description")

                    or data.get("name")

                    or data.get("title")

                    or ""

                ),

                category=str(data.get("category") or data.get("categoryDescription") or ""),

                availability=int(qty_raw),

                price=Decimal(str(price_raw)),

                cost_price=(

                    Decimal(str(data["cost_price"]))

                    if data.get("cost_price") is not None

                    else (

                        Decimal(str(data["costPrice"]))

                        if data.get("costPrice") is not None

                        else None

                    )

                ),

                manual_url=data.get("manual_url") or data.get("manualUrl"),

                datasheet_url=data.get("datasheet_url") or data.get("datasheetUrl"),

                created_at=data.get("created_at") or now,

                updated_at=data.get("updated_at") or now,

            )

        except Exception as exc:

            logger.warning("Parsing prodotto EasyOne fallito: %s", exc)

            return None


