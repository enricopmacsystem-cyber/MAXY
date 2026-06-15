from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.integrations.easyone.endpoints import EasyOneEndpoints
from app.integrations.easyone.http_client import EasyOneHttpClient
from app.integrations.easyone.response_utils import extract_easyone_items, macsystem_list_params
from app.schemas.customer import CustomerResponse

logger = get_logger(__name__)


class EasyOneCustomersClient:
    """Client CRM EasyOne — anagrafica People (MAC SYSTEM)."""

    def __init__(self, http_client: EasyOneHttpClient | None = None) -> None:
        self.http = http_client or EasyOneHttpClient()
        self.endpoints = EasyOneEndpoints.from_settings(self.http.settings)

    def list_customers(self, *, take: int = 100, skip: int = 0) -> list[CustomerResponse]:
        """Elenco paginato anagrafiche (take/skip Mac System)."""
        if skip > 0:
            return self._fetch_page(take=take, skip=skip, params=macsystem_list_params(take=take, skip=skip))

        param_sets = (
            macsystem_list_params(take=take, skip=skip),
            {"take": take, "skip": skip, "searchValue": ""},
            {"take": take, "skip": skip, "searchValue": "%"},
        )
        for params in param_sets:
            batch = self._fetch_page(take=take, skip=skip, params=params)
            if batch:
                return batch
        return []

    def _fetch_page(
        self,
        *,
        take: int,
        skip: int,
        params: dict[str, Any],
    ) -> list[CustomerResponse]:
        try:
            data = self.http.get(self.endpoints.customers_search, params=params)
        except Exception as exc:
            logger.debug("EasyOne people list %s: %s", params, exc)
            return []

        results: list[CustomerResponse] = []
        seen: set[str] = set()
        for item in extract_easyone_items(data):
            parsed = self._parse_customer(item)
            if parsed and parsed.customer_code not in seen:
                seen.add(parsed.customer_code)
                results.append(parsed)

        if len(results) > take:
            return results[:take]
        return results

    def search(self, query: str, *, limit: int = 20) -> list[CustomerResponse]:
        params = macsystem_list_params(take=limit, skip=0, search_value=query)
        try:
            data = self.http.get(self.endpoints.customers_search, params=params)
        except Exception as exc:
            logger.warning("EasyOne people search non disponibile: %s", exc)
            return []

        results: list[CustomerResponse] = []
        for item in extract_easyone_items(data)[:limit]:
            parsed = self._parse_customer(item)
            if parsed:
                results.append(parsed)
        return results

    def get_by_code(self, customer_code: str) -> CustomerResponse | None:
        if self._looks_like_guid(customer_code):
            path = self.endpoints.customer_by_code.format(code=customer_code)
            try:
                data = self.http.get(path)
            except Exception as exc:
                logger.warning("EasyOne people %s non disponibile: %s", customer_code, exc)
                return None
            if isinstance(data, dict):
                return self._parse_customer(data)

        matches = self.search(customer_code, limit=5)
        normalized = customer_code.strip().upper()
        for item in matches:
            if item.customer_code.upper() == normalized:
                return item
        return matches[0] if matches else None

    @staticmethod
    def _looks_like_guid(value: str) -> bool:
        try:
            UUID(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _display_name(data: dict[str, Any], code: str | None, guid: Any) -> str:
        name = (
            data.get("description")
            or data.get("company_name")
            or data.get("name")
            or data.get("ragione_sociale")
            or data.get("businessName")
            or data.get("companyName")
        )
        if name:
            return str(name).strip()

        first = str(data.get("firstName") or data.get("first_name") or "").strip()
        last = str(data.get("lastName") or data.get("last_name") or data.get("surname") or "").strip()
        combined = f"{first} {last}".strip()
        if combined:
            return combined

        return str(code or guid or "Cliente").strip()

    @staticmethod
    def _parse_customer(data: dict[str, Any]) -> CustomerResponse | None:
        guid = data.get("id")
        code = data.get("code") or data.get("customer_code") or data.get("customerCode")
        customer_code = str(code or guid or "").strip()
        if not customer_code:
            return None

        company_name = EasyOneCustomersClient._display_name(data, code, guid)
        addr = EasyOneCustomersClient._extract_address(data)
        now = datetime.now(UTC)
        return CustomerResponse(
            id=guid or uuid4(),
            customer_code=customer_code,
            company_name=company_name,
            vat_number=data.get("vat_number") or data.get("partita_iva") or data.get("vatNumber"),
            phone=(
                data.get("phone")
                or data.get("telefono")
                or data.get("mobilePhone")
                or data.get("phoneNumber")
                or data.get("mobile")
            ),
            email=data.get("email") or data.get("mail"),
            city=addr.get("city"),
            address_line=addr.get("address_line"),
            postal_code=addr.get("postal_code"),
            province=addr.get("province"),
            country=addr.get("country"),
            latitude=addr.get("latitude"),
            longitude=addr.get("longitude"),
            sales_agent=data.get("sales_agent") or data.get("agente") or data.get("agentName"),
            source_system="easyone",
            fetched_at=data.get("fetched_at") or now,
        )

    @staticmethod
    def _extract_address(data: dict[str, Any]) -> dict[str, Any]:
        block = data.get("address") if isinstance(data.get("address"), dict) else data
        line = (
            block.get("address")
            or block.get("addressLine")
            or block.get("street")
            or block.get("streetName")
            or data.get("addressLine")
            or data.get("street")
            or data.get("fullAddress")
        )
        if isinstance(line, list):
            line = ", ".join(str(part) for part in line if part)
        city = (
            block.get("city")
            or block.get("town")
            or block.get("citta")
            or data.get("city")
            or data.get("town")
        )
        postal = (
            block.get("postalCode")
            or block.get("zipCode")
            or block.get("cap")
            or data.get("postalCode")
            or data.get("zipCode")
        )
        province = (
            block.get("province")
            or block.get("state")
            or block.get("region")
            or data.get("province")
            or data.get("state")
        )
        country = block.get("country") or data.get("country") or data.get("nation")

        lat = block.get("latitude") or block.get("lat") or data.get("latitude")
        lon = block.get("longitude") or block.get("lng") or data.get("longitude")
        geo = block.get("geoLocation") or block.get("location") or data.get("geoLocation")
        if isinstance(geo, dict):
            lat = lat or geo.get("latitude") or geo.get("lat")
            lon = lon or geo.get("longitude") or geo.get("lng")

        def _to_decimal(value: Any) -> Decimal | None:
            if value is None or value == "":
                return None
            try:
                return Decimal(str(value))
            except Exception:
                return None

        return {
            "address_line": str(line).strip() if line else None,
            "city": str(city).strip() if city else None,
            "postal_code": str(postal).strip() if postal else None,
            "province": str(province).strip() if province else None,
            "country": str(country).strip() if country else None,
            "latitude": _to_decimal(lat),
            "longitude": _to_decimal(lon),
        }
