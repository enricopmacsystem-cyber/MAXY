from __future__ import annotations



from datetime import date, datetime

from decimal import Decimal

from typing import Any



from app.core.logging import get_logger

from app.integrations.easyone.endpoints import EasyOneEndpoints

from app.integrations.easyone.http_client import EasyOneHttpClient

from app.integrations.easyone.response_utils import extract_easyone_items, macsystem_list_params



logger = get_logger(__name__)





class EasyOneOrdersClient:

    """Client ordini EasyOne/ERP (joborders Mac System)."""



    def __init__(self, http_client: EasyOneHttpClient | None = None) -> None:

        self.http = http_client or EasyOneHttpClient()

        self.endpoints = EasyOneEndpoints.from_settings(self.http.settings)



    def search(

        self,

        *,

        customer_code: str | None = None,

        from_date: date | None = None,

        limit: int = 100,

        skip: int = 0,

    ) -> list[dict[str, Any]]:

        params = macsystem_list_params(take=limit, skip=skip)

        params["limit"] = limit

        if customer_code:

            params["customer_code"] = customer_code

            params["customerCode"] = customer_code

        if from_date:

            params["from_date"] = from_date.isoformat()

            params["fromDate"] = from_date.isoformat()

        try:

            data = self.http.get(self.endpoints.orders_search, params=params)

        except Exception as exc:

            logger.warning("EasyOne orders search non disponibile: %s", exc)

            return []

        return extract_easyone_items(data)



    def get_order(self, order_number: str) -> dict[str, Any] | None:

        path = self.endpoints.order_by_number.format(order_number=order_number)

        try:

            data = self.http.get(path)

        except Exception as exc:

            logger.warning("EasyOne order %s non disponibile: %s", order_number, exc)

            return None

        return data if isinstance(data, dict) else None



    @staticmethod

    def parse_order_line(line: dict[str, Any]) -> dict[str, Any] | None:

        article = line.get("article") if isinstance(line.get("article"), dict) else {}

        code = (

            line.get("product_code")

            or line.get("internal_code")

            or line.get("sku")

            or line.get("articleCode")

            or line.get("code")

            or article.get("code")

            or article.get("articleCode")

        )

        if not code:

            return None

        qty = line.get("quantity") or line.get("qty") or line.get("amount") or "1"

        price = line.get("unit_price") or line.get("unitPrice") or line.get("price")

        return {

            "product_code": str(code),

            "quantity": Decimal(str(qty)),

            "unit_price": Decimal(str(price)) if price is not None else None,

        }



    def parse_order(self, header: dict[str, Any]) -> dict[str, Any] | None:

        number = (

            header.get("order_number")

            or header.get("numero_ordine")

            or header.get("number")

            or header.get("code")

            or header.get("documentNumber")

            or header.get("jobOrderNumber")

        )

        if not number:

            return None



        order_date_raw = (

            header.get("order_date")

            or header.get("data_ordine")

            or header.get("date")

            or header.get("documentDate")

            or header.get("creationDate")

            or header.get("createdDate")

        )

        if isinstance(order_date_raw, str):

            order_date = date.fromisoformat(order_date_raw[:10])

        elif isinstance(order_date_raw, datetime):

            order_date = order_date_raw.date()

        else:

            order_date = date.today()



        customer_code = header.get("customer_code") or header.get("customerCode")

        customer = header.get("customer")

        if not customer_code and isinstance(customer, dict):

            customer_code = customer.get("code") or customer.get("customerCode")



        lines = (

            header.get("lines")

            or header.get("righe")

            or header.get("rows")

            or header.get("jobOrderRows")

            or header.get("details")

            or header.get("items")

            or []

        )

        if not lines:

            detail = self.get_order(str(number))

            if detail:

                lines = (

                    detail.get("lines")

                    or detail.get("righe")

                    or detail.get("rows")

                    or detail.get("jobOrderRows")

                    or detail.get("details")

                    or detail.get("items")

                    or []

                )

                if not customer_code and isinstance(detail.get("customer"), dict):

                    customer_code = detail["customer"].get("code")



        parsed_lines = [

            self.parse_order_line(line) for line in lines if isinstance(line, dict)

        ]

        return {

            "order_number": str(number),

            "order_date": order_date,

            "customer_code": str(customer_code) if customer_code else None,

            "lines": [line for line in parsed_lines if line],

        }


