from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.easyone.context import build_easyone_client
from app.integrations.easyone.customers_client import EasyOneCustomersClient
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer import CustomerResponse, CustomerSearchResponse

logger = get_logger(__name__)


class CustomerService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = CustomerRepository(session)

    def list_cached(
        self,
        *,
        query: str = "",
        limit: int = 2000,
        offset: int = 0,
    ) -> CustomerSearchResponse:
        cleaned = query.strip()
        if cleaned:
            items, total = self.repo.search(cleaned, limit=limit, offset=offset)
        else:
            items, total = self.repo.list_all(limit=limit, offset=offset)
        return CustomerSearchResponse(
            items=[CustomerResponse.model_validate(item) for item in items],
            total=total,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
        easyone_access_token: str | None = None,
    ) -> CustomerSearchResponse:
        cleaned = query.strip()
        if not cleaned:
            return self.list_cached(limit=limit, offset=offset)

        remote_items: list[CustomerResponse] = []
        http = build_easyone_client(self.settings, access_token=easyone_access_token)
        if http:
            client = EasyOneCustomersClient(http)
            remote_items = client.search(cleaned, limit=limit)
            if remote_items:
                self._upsert_cache(remote_items)
                self.session.commit()
                return CustomerSearchResponse(items=remote_items, total=len(remote_items))

        items, total = self.repo.search(cleaned, limit=limit, offset=offset)
        return CustomerSearchResponse(
            items=[CustomerResponse.model_validate(item) for item in items],
            total=total,
        )

    def get_by_code(
        self,
        customer_code: str,
        *,
        easyone_access_token: str | None = None,
    ) -> CustomerResponse | None:
        http = build_easyone_client(self.settings, access_token=easyone_access_token)
        if http:
            client = EasyOneCustomersClient(http)
            remote = client.get_by_code(customer_code)
            if remote:
                self._upsert_cache([remote])
                self.session.commit()
                return remote

        item = self.repo.get_by_code(customer_code)
        return CustomerResponse.model_validate(item) if item else None

    def sync_all_from_easyone(self, *, easyone_access_token: str | None = None) -> dict:
        http = build_easyone_client(self.settings, access_token=easyone_access_token)
        if not http:
            return {"imported": 0, "updated": 0, "total": self.repo.count_all()}

        client = EasyOneCustomersClient(http)
        page_size = 200
        max_pages = 250
        imported = 0
        updated = 0
        skip = 0
        seen_signatures: set[frozenset[str]] = set()

        for _page in range(max_pages):
            batch = client.list_customers(take=page_size, skip=skip)
            if not batch:
                break

            signature = frozenset(customer.customer_code for customer in batch)
            if signature in seen_signatures:
                logger.warning(
                    "Sync clienti EasyOne: pagina duplicata a skip=%s, stop paginazione",
                    skip,
                )
                break
            seen_signatures.add(signature)

            for customer in batch:
                if self.repo.upsert_from_easyone(customer):
                    imported += 1
                else:
                    updated += 1

            if len(batch) < page_size:
                break
            skip += len(batch)

        self.session.commit()
        total = self.repo.count_all()
        logger.info(
            "Sync clienti EasyOne: %s nuovi, %s aggiornati, %s in archivio",
            imported,
            updated,
            total,
        )
        return {"imported": imported, "updated": updated, "total": total}

    def _upsert_cache(self, customers: list[CustomerResponse]) -> None:
        for customer in customers:
            self.repo.upsert_from_easyone(customer)
        if customers:
            self.session.flush()
