from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import ProductNotFoundError
from app.core.logging import get_logger
from app.integrations.easyone.http_client import EasyOneHttpClient
from app.integrations.easyone.products_client import EasyOneProductsClient
from app.models.order import Order, OrderLine
from app.models.product import Product
from app.repositories.order_repo import RecommendationRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.chat import AvailabilityInfo, DocumentationInfo, SourceCitation
from app.schemas.product import ProductResponse
from app.schemas.recommendation import PurchaseFrequency
from app.utils.availability import availability_info

logger = get_logger(__name__)


@dataclass(frozen=True)
class EasyOneProductBundle:
    """Dati articolo recuperati da EasyOne / ERP (fonte unificata)."""

    product: ProductResponse
    availability: AvailabilityInfo
    sales_history: PurchaseFrequency
    last_order_date: date | None
    documentation: DocumentationInfo
    source: str = "easyone_local_adapter"


class EasyOneAdapter(ABC):
    """Contratto adapter EasyOne — sostituibile con client HTTP reale."""

    @abstractmethod
    def get_product_by_code(self, internal_code: str) -> EasyOneProductBundle:
        raise NotImplementedError

    @abstractmethod
    def resolve_product_query(self, query: str) -> EasyOneProductBundle:
        """Risolve codice esatto o ricerca libera verso un articolo primario."""
        raise NotImplementedError


class LocalEasyOneAdapter(EasyOneAdapter):
    """
    Adapter locale che simula EasyOne usando PostgreSQL sincronizzato con ERP.

    In produzione: sostituire con EasyOneApiAdapter che chiama REST EasyOne/ERP.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.product_repository = ProductRepository(session)
        self.recommendation_repository = RecommendationRepository(session)

    def get_product_by_code(self, internal_code: str) -> EasyOneProductBundle:
        product = self.product_repository.get_by_internal_code(internal_code)
        if not product:
            raise ProductNotFoundError(
                f"Articolo '{internal_code}' non trovato in EasyOne/ERP"
            )
        return self._build_bundle(product)

    def resolve_product_query(self, query: str) -> EasyOneProductBundle:
        cleaned = query.strip()
        if not cleaned:
            raise ProductNotFoundError("Query prodotto vuota")

        product = self.product_repository.get_by_internal_code(cleaned)
        if product:
            logger.info("Commercial Copilot: match esatto codice %s", cleaned)
            return self._build_bundle(product)

        hits, _ = self.product_repository.search_fulltext(cleaned, limit=1)
        if not hits:
            raise ProductNotFoundError(
                f"Nessun articolo trovato in EasyOne per: {cleaned}"
            )

        logger.info(
            "Commercial Copilot: match ricerca '%s' → %s",
            cleaned,
            hits[0].product.internal_code,
        )
        return self._build_bundle(hits[0].product)

    def _build_bundle(self, product: Product) -> EasyOneProductBundle:
        product_response = ProductResponse.model_validate(product)
        stats = self.recommendation_repository.get_stats(product.id)

        if stats:
            sales_history = PurchaseFrequency(
                order_count=stats.order_count,
                line_count=stats.line_count,
                total_quantity=stats.total_quantity,
            )
        else:
            sales_history = PurchaseFrequency(
                order_count=0,
                line_count=0,
                total_quantity=Decimal("0"),
            )

        last_order_date = self._get_last_order_date(product.id)
        documentation = DocumentationInfo(
            manual_url=str(product.manual_url) if product.manual_url else None,
            datasheet_url=str(product.datasheet_url) if product.datasheet_url else None,
            pdf_sources=[],
            technical_summary="",
        )

        return EasyOneProductBundle(
            product=product_response,
            availability=availability_info(product_response),
            sales_history=sales_history,
            last_order_date=last_order_date,
            documentation=documentation,
            source="easyone_local_adapter",
        )

    def _get_last_order_date(self, product_id) -> date | None:
        stmt = (
            select(func.max(Order.order_date))
            .join(OrderLine, OrderLine.order_id == Order.id)
            .where(OrderLine.product_id == product_id)
        )
        result = self.session.scalar(stmt)
        return result


class HttpEasyOneAdapter(EasyOneAdapter):
    """
    Adapter HTTP verso EasyOne/ERP con fallback locale per dati analitici.

    In produzione: articoli e giacenze da API live; storico ordini da sync/cache locale.
    """

    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        access_token: str | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.local_fallback = LocalEasyOneAdapter(session)
        http_client = EasyOneHttpClient(self.settings, access_token=access_token)
        self.products_client = EasyOneProductsClient(http_client)

    def get_product_by_code(self, internal_code: str) -> EasyOneProductBundle:
        remote = self.products_client.get_product_by_code(internal_code)
        if remote:
            logger.info("HttpEasyOneAdapter: articolo %s da API", internal_code)
            return self._bundle_from_remote(remote)
        logger.info(
            "HttpEasyOneAdapter: fallback locale per codice %s", internal_code
        )
        return self.local_fallback.get_product_by_code(internal_code)

    def resolve_product_query(self, query: str) -> EasyOneProductBundle:
        cleaned = query.strip()
        if not cleaned:
            raise ProductNotFoundError("Query prodotto vuota")

        remote = self.products_client.get_product_by_code(cleaned)
        if remote:
            return self._bundle_from_remote(remote)

        hits = self.products_client.search_products(cleaned, limit=1)
        if hits:
            return self._bundle_from_remote(hits[0])

        return self.local_fallback.resolve_product_query(cleaned)

    def _bundle_from_remote(self, product: ProductResponse) -> EasyOneProductBundle:
        try:
            local_bundle = self.local_fallback.get_product_by_code(
                product.internal_code
            )
            return EasyOneProductBundle(
                product=product,
                availability=availability_info(product),
                sales_history=local_bundle.sales_history,
                last_order_date=local_bundle.last_order_date,
                documentation=local_bundle.documentation,
                source="easyone_http_adapter",
            )
        except ProductNotFoundError:
            return EasyOneProductBundle(
                product=product,
                availability=availability_info(product),
                sales_history=PurchaseFrequency(
                    order_count=0,
                    line_count=0,
                    total_quantity=Decimal("0"),
                ),
                last_order_date=None,
                documentation=DocumentationInfo(
                    manual_url=str(product.manual_url) if product.manual_url else None,
                    datasheet_url=(
                        str(product.datasheet_url) if product.datasheet_url else None
                    ),
                    pdf_sources=[],
                    technical_summary="",
                ),
                source="easyone_http_adapter",
            )
