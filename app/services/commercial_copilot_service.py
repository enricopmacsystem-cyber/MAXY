from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import ChatCompletionError, CopilotError, ProductNotFoundError
from app.core.logging import get_logger
from app.integrations.easyone.adapter import EasyOneAdapter, EasyOneProductBundle
from app.integrations.easyone.factory import get_easyone_adapter
from app.integrations.openai.chat import ChatService
from app.integrations.qdrant.retriever import QdrantRetriever, optional_qdrant_retriever
from app.models.product import Product
from app.repositories.product_repo import ProductRepository
from app.schemas.chat import SourceCitation
from app.schemas.commercial_copilot import (
    CommercialCopilotRequest,
    CommercialCopilotResponse,
    CopilotProductInsight,
    SalesHistoryDetail,
)
from app.schemas.compatibility import ProductCompatibilityBundle
from app.schemas.product import ProductResponse
from app.services.compatibility_service import CompatibilityService
from app.services.recommendation_service import RecommendationService
from app.utils.margin import calculate_margin_percent

logger = get_logger(__name__)


@dataclass(frozen=True)
class _CopilotAnalysis:
    compatibility: list[CopilotProductInsight]
    alternatives: list[CopilotProductInsight]
    bought_together: list[CopilotProductInsight]
    similar_products: list[CopilotProductInsight]
    complementary: list[CopilotProductInsight]
    higher_margin: list[CopilotProductInsight]
    cross_selling: list[CopilotProductInsight]


class CommercialCopilotService:
    """
    Modalità Commercial Copilot.

    1. Recupera da EasyOne: articolo, disponibilità, storico, categoria, produttore, documenti
    2. Analizza: simili, compatibili, acquistati insieme, margine superiore, complementari
    3. Genera report strutturato + sintesi AI
    """

    def __init__(
        self,
        session: Session,
        *,
        easyone_adapter: EasyOneAdapter | None = None,
        retriever: QdrantRetriever | None = None,
        chat_service: ChatService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.easyone = easyone_adapter or get_easyone_adapter(session, self.settings)
        self.product_repository = ProductRepository(session)
        self.compatibility_service = CompatibilityService(session)
        self.recommendation_service = RecommendationService(session)
        self.retriever = (
            retriever
            if retriever is not None
            else optional_qdrant_retriever(settings=self.settings)
        )
        self.chat_service = chat_service or ChatService(settings=self.settings)

    def analyze(self, request: CommercialCopilotRequest) -> CommercialCopilotResponse:
        query = request.query.strip()
        logger.debug("Commercial Copilot avviato per: %s", query)

        try:
            bundle = self.easyone.resolve_product_query(query)
        except ProductNotFoundError as exc:
            raise CopilotError(str(exc)) from exc

        product_entity = self.product_repository.get_by_internal_code(
            bundle.product.internal_code
        )
        if not product_entity:
            raise CopilotError("Articolo non trovato nel repository locale")

        bundle = self._enrich_documentation(bundle, product_entity, query)
        analysis = self._run_analysis(
            product_entity,
            bundle.product,
            limit=request.limit_per_section,
        )

        ai_summary = ""
        if request.include_ai_summary:
            try:
                ai_summary = self.chat_service.generate_copilot_summary(
                    bundle=bundle,
                    analysis=analysis,
                )
            except ChatCompletionError as exc:
                logger.warning("Sintesi AI Copilot non disponibile: %s", exc)
                ai_summary = self._fallback_summary(bundle, analysis)

        response = CommercialCopilotResponse(
            query=query,
            requested_product=bundle.product,
            availability=bundle.availability,
            sales_history=SalesHistoryDetail(
                order_count=bundle.sales_history.order_count,
                line_count=bundle.sales_history.line_count,
                total_quantity=bundle.sales_history.total_quantity,
                last_order_date=bundle.last_order_date,
            ),
            documentation=bundle.documentation,
            compatibility=analysis.compatibility,
            alternatives=analysis.alternatives,
            bought_together=analysis.bought_together,
            similar_products=analysis.similar_products,
            complementary=analysis.complementary,
            higher_margin_opportunities=analysis.higher_margin,
            cross_selling_opportunities=analysis.cross_selling,
            ai_summary=ai_summary,
            formatted_report=self._format_report(bundle, analysis, ai_summary),
        )

        logger.info(
            "Commercial Copilot completato per %s",
            bundle.product.internal_code,
        )
        return response

    def _enrich_documentation(
        self,
        bundle: EasyOneProductBundle,
        product: Product,
        query: str,
    ) -> EasyOneProductBundle:
        from urllib.parse import urlparse

        pdf_filter = None
        if product.manual_url:
            pdf_filter = urlparse(product.manual_url).path.rsplit("/", 1)[-1] or None
        if not pdf_filter and product.datasheet_url:
            pdf_filter = urlparse(product.datasheet_url).path.rsplit("/", 1)[-1] or None

        chunks = []
        if self.retriever:
            try:
                chunks = self.retriever.search(
                    query=query, top_k=3, source_file=pdf_filter
                )
                if not chunks and pdf_filter:
                    chunks = self.retriever.search(query=query, top_k=3)
            except Exception as exc:
                logger.warning("Ricerca PDF Copilot fallita: %s", exc)
                chunks = []

        pdf_sources = [
            SourceCitation(
                pdf_name=chunk.source_file,
                page=chunk.page_number,
                section=chunk.section,
            )
            for chunk in chunks
        ]

        technical_summary = ""
        if chunks:
            technical_summary = chunks[0].content[:400].strip()

        documentation = bundle.documentation.model_copy(
            update={
                "pdf_sources": pdf_sources,
                "technical_summary": technical_summary,
            }
        )
        return EasyOneProductBundle(
            product=bundle.product,
            availability=bundle.availability,
            sales_history=bundle.sales_history,
            last_order_date=bundle.last_order_date,
            documentation=documentation,
            source=bundle.source,
        )

    def _run_analysis(
        self,
        product: Product,
        product_response: ProductResponse,
        *,
        limit: int,
    ) -> _CopilotAnalysis:
        compatibility_bundle = self.compatibility_service.get_bundle_for_product(product)
        recommendations = self.recommendation_service.get_recommendations_for_product(
            product.internal_code,
            limit=limit,
        )

        anchor_margin = calculate_margin_percent(product.price, product.cost_price)

        compatibility = self._from_compat_group(
            compatibility_bundle.accessories,
            label="Accessorio compatibile",
        )
        alternatives = self._from_compat_group(
            compatibility_bundle.alternatives,
            label="Alternativa",
        )
        complementary = self._from_compat_group(
            compatibility_bundle.complementary,
            label="Prodotto complementare",
        )
        spare_parts = self._from_compat_group(
            compatibility_bundle.spare_parts,
            label="Ricambio",
        )
        compatibility = compatibility + spare_parts

        bought_together = [
            self._to_insight(
                ProductResponse.model_validate(item.product),
                reason=(
                    f"Acquistato insieme nel {item.correlation_percent}% "
                    f"degli ordini"
                ),
                correlation_percent=item.correlation_percent,
            )
            for item in recommendations.bought_together[:limit]
        ]

        similar_entities = self.product_repository.find_similar_products(
            product,
            limit=limit,
        )
        similar_products = [
            self._to_insight(
                ProductResponse.model_validate(p),
                reason="Prodotto simile (stessa categoria)",
            )
            for p in similar_entities
        ]

        higher_margin_entities = self.product_repository.find_higher_margin_products(
            product,
            anchor_margin=anchor_margin,
            limit=limit,
        )
        higher_margin = [
            self._to_insight(
                ProductResponse.model_validate(p),
                reason=self._margin_reason(anchor_margin, p),
            )
            for p in higher_margin_entities
        ]

        cross_selling = self._build_cross_selling(
            bought_together=bought_together,
            complementary=complementary,
            higher_margin=higher_margin,
            limit=limit,
        )

        return _CopilotAnalysis(
            compatibility=compatibility[:limit],
            alternatives=alternatives[:limit],
            bought_together=bought_together,
            similar_products=similar_products,
            complementary=complementary[:limit],
            higher_margin=higher_margin,
            cross_selling=cross_selling,
        )

    @staticmethod
    def _from_compat_group(
        items,
        *,
        label: str,
    ) -> list[CopilotProductInsight]:
        results: list[CopilotProductInsight] = []
        for item in items:
            note = f" — {item.notes}" if item.notes else ""
            results.append(
                CommercialCopilotService._to_insight(
                    item.product,
                    reason=f"{label}{note}",
                )
            )
        return results

    @staticmethod
    def _to_insight(
        product: ProductResponse,
        *,
        reason: str | None = None,
        correlation_percent: Decimal | None = None,
    ) -> CopilotProductInsight:
        margin = calculate_margin_percent(product.price, product.cost_price)
        return CopilotProductInsight(
            internal_code=product.internal_code,
            description=product.description,
            manufacturer=product.manufacturer,
            category=product.category,
            price=product.price,
            availability=product.availability,
            margin_percent=margin,
            correlation_percent=correlation_percent,
            reason=reason,
        )

    @staticmethod
    def _margin_reason(
        anchor_margin: Decimal | None,
        product: Product,
    ) -> str:
        margin = calculate_margin_percent(product.price, product.cost_price)
        if anchor_margin is not None and margin is not None:
            delta = margin - anchor_margin
            return f"Margine superiore (+{delta}% vs articolo richiesto)"
        return "Fascia prezzo superiore nella stessa categoria"

    @staticmethod
    def _build_cross_selling(
        *,
        bought_together: list[CopilotProductInsight],
        complementary: list[CopilotProductInsight],
        higher_margin: list[CopilotProductInsight],
        limit: int,
    ) -> list[CopilotProductInsight]:
        merged: list[CopilotProductInsight] = []
        seen: set[str] = set()

        for group in (bought_together, complementary, higher_margin):
            for item in group:
                if item.internal_code in seen:
                    continue
                seen.add(item.internal_code)
                merged.append(
                    CopilotProductInsight(
                        **item.model_dump(),
                        reason=f"Cross-sell: {item.reason or 'opportunità commerciale'}",
                    )
                )
                if len(merged) >= limit:
                    return merged
        return merged

    @staticmethod
    def _format_report(
        bundle: EasyOneProductBundle,
        analysis: _CopilotAnalysis,
        ai_summary: str,
    ) -> str:
        product = bundle.product
        lines = [
            "=== COMMERCIAL COPILOT ===",
            "",
            "Prodotto richiesto:",
            f"  {product.internal_code} — {product.description}",
            f"  Produttore: {product.manufacturer}",
            f"  Categoria: {product.category}",
            f"  Prezzo: {product.price} EUR",
            "",
            "Disponibilità:",
            f"  {bundle.availability.status_label}",
            "",
            "Storico vendite:",
            f"  Ordini: {bundle.sales_history.order_count} | "
            f"Quantità totale: {bundle.sales_history.total_quantity}",
        ]
        if bundle.last_order_date:
            lines.append(f"  Ultimo ordine: {bundle.last_order_date}")

        lines.extend(["", "Compatibilità:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.compatibility))

        lines.extend(["", "Alternative:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.alternatives))

        lines.extend(["", "Prodotti acquistati insieme:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.bought_together))

        lines.extend(["", "Prodotti simili:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.similar_products))

        lines.extend(["", "Complementari:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.complementary))

        lines.extend(["", "Opportunità margine superiore:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.higher_margin))

        lines.extend(["", "Opportunità di cross selling:"])
        lines.extend(CommercialCopilotService._format_insight_lines(analysis.cross_selling))

        if ai_summary:
            lines.extend(["", "Sintesi AI:", ai_summary])

        return "\n".join(lines)

    @staticmethod
    def _format_insight_lines(items: list[CopilotProductInsight]) -> list[str]:
        if not items:
            return ["  (nessuno)"]
        result: list[str] = []
        for item in items:
            suffix = ""
            if item.correlation_percent is not None:
                suffix = f" ({item.correlation_percent}%)"
            elif item.margin_percent is not None:
                suffix = f" (margine {item.margin_percent}%)"
            result.append(f"  - {item.internal_code} — {item.description}{suffix}")
        return result

    @staticmethod
    def _fallback_summary(
        bundle: EasyOneProductBundle,
        analysis: _CopilotAnalysis,
    ) -> str:
        product = bundle.product
        parts = [
            f"Articolo {product.internal_code} disponibile con "
            f"{bundle.availability.quantity} pezzi.",
        ]
        if analysis.bought_together:
            top = analysis.bought_together[0]
            parts.append(
                f"Suggerito cross-sell: {top.internal_code} "
                f"({top.correlation_percent or '?'}% co-occorrenza)."
            )
        if analysis.higher_margin:
            parts.append(
                f"Opportunità up-sell: {analysis.higher_margin[0].internal_code}."
            )
        return " ".join(parts)
