from __future__ import annotations



from collections import defaultdict

from decimal import Decimal, ROUND_HALF_UP



from sqlalchemy import func, select

from sqlalchemy.orm import Session



from app.config.settings import Settings, get_settings

from app.integrations.easyone.context import build_easyone_client

from app.integrations.easyone.customers_client import EasyOneCustomersClient

from app.integrations.easyone.orders_client import EasyOneOrdersClient

from app.integrations.easyone.products_client import EasyOneProductsClient

from app.integrations.gemini.chat import ChatService

from app.models.order import Order, ProductOrderStats

from app.models.product import Product

from app.repositories.customer_repo import CustomerRepository

from app.repositories.order_repo import OrderRepository, RecommendationRepository

from app.repositories.product_repo import ProductRepository

from app.schemas.analytics import (

    CustomerAnalyticsResponse,

    CustomerBrandBreakdown,

    CustomerMaxySuggestionItem,

    CustomerMaxySuggestionsResponse,

    CustomerProductPurchase,

    ProductSalesStats,

    SalesAnalyticsResponse,

)

from app.schemas.product import ProductResponse

from app.services.recommendation_service import RecommendationService

from app.utils.margin import calculate_margin_percent





def _discount_from_margin(margin: Decimal | None) -> tuple[Decimal, Decimal]:

    """Ritorna (sconto massimo %, sconto consigliato %) preservando margine minimo."""

    if margin is None or margin <= Decimal("5"):

        return Decimal("0"), Decimal("0")

    max_discount = min(margin - Decimal("5"), Decimal("25"))

    max_discount = max(Decimal("0"), max_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    suggested = (max_discount * Decimal("0.65")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return max_discount, suggested





class AnalyticsService:

    def __init__(self, session: Session, settings: Settings | None = None) -> None:

        self.session = session

        self.settings = settings or get_settings()

        self.recommendation_service = RecommendationService(session)

        self.order_repo = OrderRepository(session)

        self.recommendation_repo = RecommendationRepository(session)

        self.customer_repo = CustomerRepository(session)

        self.product_repo = ProductRepository(session)



    def get_sales_overview(self, *, top_n: int = 10) -> SalesAnalyticsResponse:

        total_orders = self.session.scalar(select(func.count()).select_from(Order)) or 0



        stats_stmt = (

            select(ProductOrderStats)

            .order_by(ProductOrderStats.order_count.desc())

            .limit(top_n)

        )

        stats_rows = list(self.session.scalars(stats_stmt))



        top_products: list[ProductSalesStats] = []

        for stats in stats_rows:

            product = self.session.get(Product, stats.product_id)

            if not product:

                continue

            try:

                rec = self.recommendation_service.get_recommendations_for_product(

                    product.internal_code, limit=3

                )

                correlation_top = rec.bought_together

            except Exception:

                correlation_top = []



            top_products.append(

                ProductSalesStats(

                    product=ProductResponse.model_validate(product),

                    order_count=stats.order_count,

                    total_quantity=stats.total_quantity,

                    correlation_top=correlation_top,

                )

            )



        return SalesAnalyticsResponse(

            top_products=top_products,

            total_orders=total_orders,

        )



    def get_customer_analytics(

        self,

        customer_code: str,

        *,

        easyone_access_token: str | None = None,

    ) -> CustomerAnalyticsResponse:

        code = customer_code.strip()

        if not code:

            raise ValueError("Codice cliente obbligatorio")



        company_name: str | None = None

        city: str | None = None

        sales_agent: str | None = None

        warnings: list[str] = []



        cached = self.customer_repo.get_by_code(code)

        if cached:

            company_name = cached.company_name

            city = cached.city

            sales_agent = cached.sales_agent



        http = build_easyone_client(self.settings, access_token=easyone_access_token)

        if http:

            remote = EasyOneCustomersClient(http).get_by_code(code)

            if remote:

                company_name = remote.company_name

                city = remote.city

                sales_agent = remote.sales_agent

                self.customer_repo.upsert_from_easyone(remote)

                self.session.flush()



        rows = self.order_repo.get_customer_purchase_aggregates(code)

        source = "local"

        if not rows and http:

            rows = self._aggregate_live_easyone_orders(http, code, warnings=warnings)

            source = "easyone_live" if rows else "local"



        total_qty = sum((row["total_quantity"] for row in rows), Decimal("0"))

        total_orders = self.order_repo.count_customer_orders(code)

        if not total_orders and rows:

            total_orders = max(row["order_count"] for row in rows)



        if not rows:

            warnings.append(

                "Nessun acquisto trovato per questo cliente. "

                "Eseguire «Sincronizza con EasyOne» o verificare il codice cliente."

            )

            return CustomerAnalyticsResponse(

                customer_code=code,

                company_name=company_name,

                city=city,

                sales_agent=sales_agent,

                total_orders=total_orders,

                total_quantity=total_qty,

                brands=[],

                source=source,

                warnings=warnings,

            )



        brand_map: dict[str, list[CustomerProductPurchase]] = defaultdict(list)

        for row in rows:

            product: Product = row["product"]

            qty: Decimal = row["total_quantity"]

            product_response = ProductResponse.model_validate(product)

            margin = calculate_margin_percent(product.price, product.cost_price)

            max_disc, sugg_disc = _discount_from_margin(margin)

            share = (

                (qty / total_qty * Decimal("100")).quantize(Decimal("0.01"))

                if total_qty > 0

                else Decimal("0")

            )

            brand = (product.manufacturer or "Senza brand").strip() or "Senza brand"

            brand_map[brand].append(

                CustomerProductPurchase(

                    product=product_response,

                    brand=brand,

                    total_quantity=qty,

                    order_count=row["order_count"],

                    share_percent=share,

                    brand_share_percent=Decimal("0"),

                    avg_unit_price=row.get("avg_unit_price"),

                    max_discount_percent=max_disc,

                    suggested_discount_percent=sugg_disc,

                )

            )



        brands: list[CustomerBrandBreakdown] = []

        for brand, products in sorted(

            brand_map.items(),

            key=lambda item: sum(p.total_quantity for p in item[1]),

            reverse=True,

        ):

            brand_qty = sum((p.total_quantity for p in products), Decimal("0"))

            brand_share = (

                (brand_qty / total_qty * Decimal("100")).quantize(Decimal("0.01"))

                if total_qty > 0

                else Decimal("0")

            )

            for product in products:

                if brand_qty > 0:

                    product.brand_share_percent = (

                        product.total_quantity / brand_qty * Decimal("100")

                    ).quantize(Decimal("0.01"))

            margins = [

                calculate_margin_percent(p.product.price, p.product.cost_price)

                for p in products

            ]

            valid_margins = [m for m in margins if m is not None]

            brand_margin = (

                sum(valid_margins, Decimal("0")) / Decimal(len(valid_margins))

                if valid_margins

                else None

            )

            max_disc, sugg_disc = _discount_from_margin(brand_margin)

            brands.append(

                CustomerBrandBreakdown(

                    brand=brand,

                    total_quantity=brand_qty,

                    share_percent=brand_share,

                    product_count=len(products),

                    max_discount_percent=max_disc,

                    suggested_discount_percent=sugg_disc,

                    products=sorted(

                        products,

                        key=lambda item: item.total_quantity,

                        reverse=True,

                    ),

                )

            )



        self.session.commit()

        return CustomerAnalyticsResponse(

            customer_code=code,

            company_name=company_name,

            city=city,

            sales_agent=sales_agent,

            total_orders=total_orders,

            total_quantity=total_qty,

            brands=brands,

            source=source,

            warnings=warnings,

        )



    def get_maxy_suggestions_for_customer(

        self,

        customer_code: str,

        *,

        easyone_access_token: str | None = None,

    ) -> CustomerMaxySuggestionsResponse:

        analytics = self.get_customer_analytics(

            customer_code,

            easyone_access_token=easyone_access_token,

        )

        purchased_codes = {

            product.product.internal_code

            for brand in analytics.brands

            for product in brand.products

        }



        cross_sell: list[CustomerMaxySuggestionItem] = []

        seen_codes: set[str] = set()

        top_products = [

            product

            for brand in analytics.brands

            for product in brand.products

        ][:8]



        for purchase in top_products:

            product = self.session.get(Product, purchase.product.id)

            if not product:

                continue

            hits = self.recommendation_repo.get_recommendations(product.id, limit=5)

            for hit in hits:

                code = hit.related_product.internal_code

                if code in purchased_codes or code in seen_codes:

                    continue

                seen_codes.add(code)

                cross_sell.append(

                    CustomerMaxySuggestionItem(

                        internal_code=code,

                        description=hit.related_product.description,

                        brand=hit.related_product.manufacturer or "",

                        reason=(

                            f"Acquistato spesso insieme a {purchase.product.internal_code}"

                        ),

                        correlation_percent=hit.correlation_percent,

                    )

                )

                if len(cross_sell) >= 12:

                    break

            if len(cross_sell) >= 12:

                break



        context_lines = [

            f"Cliente: {analytics.customer_code} — {analytics.company_name or ''}",

            f"Ordini: {analytics.total_orders}, quantità totale: {analytics.total_quantity}",

            "Brand acquistati:",

        ]

        for brand in analytics.brands[:10]:

            context_lines.append(

                f"  - {brand.brand}: {brand.share_percent}% "

                f"(sconto consigliato fino a {brand.suggested_discount_percent}%)"

            )

            for product in brand.products[:5]:

                context_lines.append(

                    f"      {product.product.internal_code} x{product.total_quantity} "

                    f"({product.share_percent}%)"

                )



        if cross_sell:

            context_lines.append("Cross-sell da storico:")

            for item in cross_sell[:8]:

                context_lines.append(

                    f"  - {item.internal_code} ({item.correlation_percent or 0}%)"

                )



        summary = ""

        suggestions: list[CustomerMaxySuggestionItem] = []

        try:

            chat = ChatService(settings=self.settings)

            raw = chat.generate_simple_completion(

                system_prompt=(

                    f"Sei {self.settings.ai_assistant_name}, copilota commerciale. "

                    "Analizza lo storico cliente e suggerisci cosa proporre in vendita. "

                    "Non inventare codici articolo: usa solo quelli nel contesto o cross-sell indicati. "

                    "Rispondi in italiano con: 1) breve sintesi 2) elenco puntato di proposte "

                    "(codice, motivo, eventuale sconto)."

                ),

                user_prompt="\n".join(context_lines),

            )

            summary = raw.strip()

        except Exception as exc:

            summary = f"Suggerimenti basati su cross-sell storico (Maxy non disponibile: {exc})"



        for item in cross_sell[:6]:

            suggestions.append(item)



        return CustomerMaxySuggestionsResponse(

            customer_code=analytics.customer_code,

            company_name=analytics.company_name,

            summary=summary,

            suggestions=suggestions,

            cross_sell=cross_sell,

        )



    def _aggregate_live_easyone_orders(

        self,

        http,

        customer_code: str,

        *,

        warnings: list[str],

    ) -> list[dict]:

        orders_client = EasyOneOrdersClient(http)

        products_client = EasyOneProductsClient(http)

        headers = orders_client.search(customer_code=customer_code, limit=200)

        if not headers:

            warnings.append("EasyOne: nessun joborder trovato per questo cliente.")

            return []



        agg: dict[str, dict] = {}

        for header in headers:

            parsed = orders_client.parse_order(header)

            if not parsed:

                continue

            for line in parsed.get("lines", []):

                code = line["product_code"]

                bucket = agg.setdefault(

                    code,

                    {

                        "total_quantity": Decimal("0"),

                        "order_count": 0,

                        "avg_unit_price": line.get("unit_price"),

                        "product": None,

                    },

                )

                bucket["total_quantity"] += line["quantity"]

                bucket["order_count"] += 1



        rows: list[dict] = []

        for code, bucket in agg.items():

            product = self.product_repo.get_by_internal_code(code)

            if not product:

                remote = products_client.get_product_by_code(code)

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

            if not product:

                warnings.append(f"Articolo {code} non risolto in anagrafica.")

                continue

            rows.append(

                {

                    "product": product,

                    "total_quantity": bucket["total_quantity"],

                    "order_count": bucket["order_count"],

                    "avg_unit_price": bucket.get("avg_unit_price"),

                }

            )

        return rows


