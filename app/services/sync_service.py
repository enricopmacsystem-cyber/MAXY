from __future__ import annotations



from datetime import UTC, datetime

from decimal import Decimal



from sqlalchemy.orm import Session



from app.config.settings import Settings, get_settings

from app.core.logging import get_logger

from app.integrations.easyone.context import build_easyone_client, build_erp_client


from app.integrations.easyone.orders_client import EasyOneOrdersClient

from app.integrations.easyone.products_client import EasyOneProductsClient

from app.integrations.easyone.stock_client import EasyOneStockClient

from app.repositories.customer_repo import CustomerRepository
from app.services.customer_service import CustomerService

from app.repositories.order_repo import OrderRepository

from app.repositories.product_repo import ProductRepository



logger = get_logger(__name__)



_PAGE_SIZE = 100

_MAX_PAGES = 50





class SyncService:

    """Sincronizzazione dati da EasyOne/ERP verso cache locale PostgreSQL."""



    def __init__(self, session: Session, settings: Settings | None = None) -> None:

        self.session = session

        self.settings = settings or get_settings()

        self.order_repo = OrderRepository(session)

        self.product_repo = ProductRepository(session)

        self.customer_repo = CustomerRepository(session)



    def sync_full_from_easyone(

        self,

        *,

        easyone_access_token: str | None = None,

        order_limit: int = 200,

    ) -> dict:

        """Importa articoli, giacenze, clienti e ordini da EasyOne."""

        http = build_easyone_client(self.settings, access_token=easyone_access_token)

        if not http:

            return {

                "status": "skipped",

                "reason": "EasyOne HTTP non configurato o token assente",

                "products_imported": 0,

                "products_updated": 0,

                "stock_updated": 0,

                "customers_imported": 0,
                "customers_updated": 0,
                "customers_in_archive": 0,

                "orders_imported": 0,

                "lines_imported": 0,

            }



        products_client = EasyOneProductsClient(http)

        products_imported = 0

        products_updated = 0

        for page in range(_MAX_PAGES):

            batch = products_client.list_products(

                take=_PAGE_SIZE,

                skip=page * _PAGE_SIZE,

            )

            if not batch:

                break

            for remote in batch:

                _, created = self.product_repo.upsert_product(

                    internal_code=remote.internal_code,

                    manufacturer=remote.manufacturer,

                    description=remote.description,

                    category=remote.category,

                    availability=remote.availability,

                    price=remote.price,

                    manual_url=str(remote.manual_url) if remote.manual_url else None,

                    datasheet_url=str(remote.datasheet_url) if remote.datasheet_url else None,

                    cost_price=remote.cost_price,

                )

                if created:

                    products_imported += 1

                else:

                    products_updated += 1

            if len(batch) < _PAGE_SIZE:

                break



        stock_updated = 0

        erp = build_erp_client(self.settings, access_token=easyone_access_token)

        if erp:

            stock_client = EasyOneStockClient(erp)

            for page in range(_MAX_PAGES):

                batch = stock_client.list_stock(take=_PAGE_SIZE, skip=page * _PAGE_SIZE)

                if not batch:

                    break

                for item in batch:

                    product = self.product_repo.get_by_internal_code(item.product.internal_code)

                    if product:

                        product.availability = item.product.availability

                        stock_updated += 1

                    else:

                        self.product_repo.upsert_product(

                            internal_code=item.product.internal_code,

                            manufacturer=item.product.manufacturer,

                            description=item.product.description,

                            category=item.product.category,

                            availability=item.product.availability,

                            price=item.product.price,

                            manual_url=None,

                            datasheet_url=None,

                            cost_price=None,

                        )

                        products_imported += 1

                        stock_updated += 1

                if len(batch) < _PAGE_SIZE:

                    break



        customer_stats = CustomerService(self.session, self.settings).sync_all_from_easyone(
            easyone_access_token=easyone_access_token,
        )
        customers_imported = customer_stats.get("imported", 0)
        customers_updated = customer_stats.get("updated", 0)

        order_stats = self.sync_orders_from_easyone(

            easyone_access_token=easyone_access_token,

            limit=order_limit,

            products_client=products_client,

        )



        self.session.commit()

        result = {

            "status": "completed",

            "products_imported": products_imported,

            "products_updated": products_updated,

            "stock_updated": stock_updated,

            "customers_imported": customers_imported,
            "customers_updated": customers_updated,
            "customers_in_archive": customer_stats.get("total", 0),

            "orders_imported": order_stats.get("orders_imported", 0),

            "lines_imported": order_stats.get("lines_imported", 0),

            "errors": order_stats.get("errors", []),

            "synced_at": datetime.now(UTC).isoformat(),

        }

        logger.info("Sync EasyOne completa: status=%s ordini=%s", result.get("status"), result.get("orders_imported"))

        return result



    def sync_orders_from_easyone(

        self,

        *,

        easyone_access_token: str | None = None,

        limit: int = 200,

        products_client: EasyOneProductsClient | None = None,

    ) -> dict:

        http = build_easyone_client(self.settings, access_token=easyone_access_token)

        if not http:

            return {

                "status": "skipped",

                "reason": "EasyOne HTTP non configurato",

                "orders_imported": 0,

                "lines_imported": 0,

            }



        client = EasyOneOrdersClient(http)

        if products_client is None:

            products_client = EasyOneProductsClient(http)



        imported = 0

        lines = 0

        errors: list[str] = []

        headers: list[dict] = []

        for page in range(max(1, (limit + _PAGE_SIZE - 1) // _PAGE_SIZE)):

            batch = client.search(limit=_PAGE_SIZE, skip=page * _PAGE_SIZE)

            if not batch:

                break

            headers.extend(batch)

            if len(batch) < _PAGE_SIZE:

                break

        headers = headers[:limit]



        for header in headers:

            parsed = client.parse_order(header)

            if not parsed:

                continue

            try:

                order, _ = self.order_repo.upsert_order(

                    order_number=parsed["order_number"],

                    order_date=parsed["order_date"],

                    customer_code=parsed.get("customer_code"),

                )

                for line in parsed.get("lines", []):

                    product = self._ensure_product(

                        products_client,

                        line["product_code"],

                        errors=errors,

                    )

                    if not product:

                        continue

                    self.order_repo.upsert_order_line(

                        order_id=order.id,

                        product_id=product.id,

                        quantity=line["quantity"],

                        unit_price=line.get("unit_price"),

                    )

                    lines += 1

                imported += 1

            except Exception as exc:

                errors.append(f"Ordine {parsed.get('order_number')}: {exc}")



        if not headers and not errors:

            errors.append(

                "Nessun ordine/joborder ricevuto da EasyOne. "

                "Verificare endpoint EASYONE_PATH_ORDERS_SEARCH (/joborders)."

            )



        return {

            "status": "completed",

            "orders_imported": imported,

            "lines_imported": lines,

            "errors": errors[:20],

            "synced_at": datetime.now(UTC).isoformat(),

        }



    def _ensure_product(

        self,

        products_client: EasyOneProductsClient,

        product_code: str,

        *,

        errors: list[str],

    ):

        product = self.product_repo.get_by_internal_code(product_code)

        if product:

            return product



        remote = products_client.get_product_by_code(product_code)

        if remote:

            product, _ = self.product_repo.upsert_product(

                internal_code=remote.internal_code,

                manufacturer=remote.manufacturer,

                description=remote.description,

                category=remote.category,

                availability=remote.availability,

                price=remote.price,

                manual_url=str(remote.manual_url) if remote.manual_url else None,

                datasheet_url=str(remote.datasheet_url) if remote.datasheet_url else None,

                cost_price=remote.cost_price,

            )

            return product



        product, _ = self.product_repo.upsert_product(

            internal_code=product_code,

            manufacturer="",

            description=product_code,

            category="",

            availability=0,

            price=Decimal("0"),

            manual_url=None,

            datasheet_url=None,

            cost_price=None,

        )

        errors.append(f"Articolo {product_code} creato in locale senza dettagli ERP")

        return product


