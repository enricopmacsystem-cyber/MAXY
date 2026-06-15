from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import ChatCompletionError, RAGError, RetrievalError
from app.core.logging import get_logger
from app.integrations.openai.chat import ChatService
from app.integrations.qdrant.retriever import (
    QdrantRetriever,
    RetrievedChunk,
    optional_qdrant_retriever,
)
from app.repositories.product_repo import ProductRepository, ProductSearchHit
from app.schemas.chat import (
    ArticleInfo,
    AvailabilityInfo,
    CommercialAssistantResponse,
    CommercialSuggestionItem,
    DocumentationInfo,
    SourceCitation,
)
from app.schemas.compatibility import ProductCompatibilityBundle
from app.schemas.product import ProductResponse
from app.services.compatibility_service import CompatibilityService
from app.services.recommendation_service import RecommendationService
from app.utils.availability import availability_info

logger = get_logger(__name__)


@dataclass(frozen=True)
class _GatheredContext:
    question: str
    primary_product: ProductResponse | None
    catalog_hits: list[ProductSearchHit]
    pdf_chunks: list[RetrievedChunk]
    compatibility: ProductCompatibilityBundle | None
    bought_together: list[CommercialSuggestionItem]


class CommercialAssistantService:
    """
    Assistente commerciale unificato.

    Per ogni domanda:
    1. Cerca nel catalogo prodotti
    2. Cerca nei PDF indicizzati
    3. Verifica disponibilità
    4. Cerca compatibilità
    5. Cerca prodotti acquistati insieme
    """

    def __init__(
        self,
        session: Session,
        *,
        retriever: QdrantRetriever | None = None,
        chat_service: ChatService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.product_repository = ProductRepository(session)
        self.compatibility_service = CompatibilityService(session)
        self.recommendation_service = RecommendationService(session)
        self.retriever = (
            retriever
            if retriever is not None
            else optional_qdrant_retriever(settings=self.settings)
        )
        self.chat_service = chat_service or ChatService(settings=self.settings)

    def ask(
        self,
        question: str,
        source_file: str | None = None,
        top_k: int | None = None,
    ) -> CommercialAssistantResponse:
        question = question.strip()
        if not question:
            raise RAGError("La domanda non può essere vuota")

        logger.info("Assistente commerciale — nuova domanda: %s", question[:200])

        context = self._gather_context(question, source_file, top_k)

        try:
            narrative = self.chat_service.generate_commercial_answer(
                question=question,
                context=context,
            )
        except ChatCompletionError as exc:
            logger.error("Errore generazione risposta commerciale: %s", exc)
            raise RAGError(str(exc)) from exc

        return self._build_response(context, narrative)

    def _gather_context(
        self,
        question: str,
        source_file: str | None,
        top_k: int | None,
    ) -> _GatheredContext:
        catalog_hits, _ = self.product_repository.search_fulltext(
            question,
            limit=3,
        )
        primary = catalog_hits[0].product if catalog_hits else None
        primary_response = (
            ProductResponse.model_validate(primary) if primary else None
        )

        pdf_filter = source_file
        if not pdf_filter and primary:
            pdf_filter = (
                _filename_from_url(primary.manual_url)
                or _filename_from_url(primary.datasheet_url)
            )

        pdf_chunks: list[RetrievedChunk] = []
        if self.retriever:
            try:
                pdf_chunks = self.retriever.search(
                    query=question,
                    top_k=top_k,
                    source_file=pdf_filter,
                )
            except RetrievalError as exc:
                logger.warning("Ricerca PDF fallita: %s", exc)
                pdf_chunks = []

            if not pdf_chunks and pdf_filter:
                try:
                    pdf_chunks = self.retriever.search(
                        query=question,
                        top_k=top_k,
                        source_file=None,
                    )
                except RetrievalError:
                    pdf_chunks = []

        compatibility: ProductCompatibilityBundle | None = None
        bought_together: list[CommercialSuggestionItem] = []

        if primary:
            compatibility = self.compatibility_service.get_bundle_for_product(primary)
            try:
                recommendations = (
                    self.recommendation_service.get_recommendations_for_product(
                        primary.internal_code,
                        limit=5,
                    )
                )
                bought_together = [
                    CommercialSuggestionItem(
                        internal_code=item.product.internal_code,
                        description=item.product.description,
                        manufacturer=item.product.manufacturer,
                        price=item.product.price,
                        availability=item.product.availability,
                        correlation_percent=item.correlation_percent,
                        reason=(
                            f"Acquistato insieme nel {item.correlation_percent}% "
                            f"degli ordini ({item.cooccurrence_count} co-occorrenze)"
                        ),
                    )
                    for item in recommendations.bought_together
                ]
            except Exception as exc:
                logger.warning(
                    "Raccomandazioni non disponibili per %s: %s",
                    primary.internal_code,
                    exc,
                )

        logger.info(
            "Contesto raccolto: catalogo=%d, pdf=%d, compatibilità=%s, suggerimenti=%d",
            len(catalog_hits),
            len(pdf_chunks),
            primary.internal_code if primary else "—",
            len(bought_together),
        )

        return _GatheredContext(
            question=question,
            primary_product=primary_response,
            catalog_hits=catalog_hits,
            pdf_chunks=pdf_chunks,
            compatibility=compatibility,
            bought_together=bought_together,
        )

    def _build_response(
        self,
        context: _GatheredContext,
        narrative: dict,
    ) -> CommercialAssistantResponse:
        product = context.primary_product
        pdf_sources = [
            SourceCitation(
                pdf_name=chunk.source_file,
                page=chunk.page_number,
                section=chunk.section,
            )
            for chunk in context.pdf_chunks
        ]

        commercial_suggestions = self._merge_suggestions(
            context.bought_together,
            context.compatibility,
        )

        documentation = DocumentationInfo(
            manual_url=str(product.manual_url) if product and product.manual_url else None,
            datasheet_url=(
                str(product.datasheet_url) if product and product.datasheet_url else None
            ),
            pdf_sources=pdf_sources,
            technical_summary=str(narrative.get("technical_summary", "")).strip(),
        )

        return CommercialAssistantResponse(
            answer=str(narrative.get("answer", "")).strip(),
            article=(
                ArticleInfo(
                    internal_code=product.internal_code,
                    manufacturer=product.manufacturer,
                    category=product.category,
                    price=product.price,
                )
                if product
                else None
            ),
            availability=availability_info(product) if product else None,
            description=product.description if product else None,
            documentation=documentation,
            compatibility=context.compatibility,
            commercial_suggestions=commercial_suggestions,
            catalog_matches=len(context.catalog_hits),
            pdf_chunks_found=len(context.pdf_chunks),
        )

    @staticmethod
    def _merge_suggestions(
        bought_together: list[CommercialSuggestionItem],
        compatibility: ProductCompatibilityBundle | None,
    ) -> list[CommercialSuggestionItem]:
        merged: list[CommercialSuggestionItem] = []
        seen: set[str] = set()

        for item in bought_together:
            if item.internal_code not in seen:
                seen.add(item.internal_code)
                merged.append(item)

        if compatibility:
            compat_groups = [
                (compatibility.accessories, "Accessorio compatibile"),
                (compatibility.complementary, "Prodotto complementare"),
                (compatibility.alternatives, "Alternativa disponibile"),
                (compatibility.spare_parts, "Ricambio disponibile"),
            ]
            for group, label in compat_groups:
                for related in group:
                    code = related.product.internal_code
                    if code in seen:
                        continue
                    seen.add(code)
                    note = f" — {related.notes}" if related.notes else ""
                    merged.append(
                        CommercialSuggestionItem(
                            internal_code=code,
                            description=related.product.description,
                            manufacturer=related.product.manufacturer,
                            price=related.product.price,
                            availability=related.product.availability,
                            reason=f"{label}{note}",
                            correlation_percent=None,
                        )
                    )

        return merged[:10]


def _filename_from_url(url: str | None) -> str | None:
    if not url:
        return None
    path = urlparse(url).path
    filename = path.rsplit("/", 1)[-1].strip()
    return filename or None
