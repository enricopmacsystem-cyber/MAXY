from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.product import ProductResponse


class PurchaseFrequency(BaseModel):
    order_count: int = Field(..., description="Numero ordini distinti con questo articolo")
    line_count: int = Field(..., description="Numero righe ordine totali")
    total_quantity: Decimal = Field(..., description="Quantità totale acquistata")


class BoughtTogetherItem(BaseModel):
    product: ProductResponse
    cooccurrence_count: int = Field(..., description="Numero ordini in cui compaiono insieme")
    correlation_percent: Decimal = Field(
        ...,
        description="Percentuale di correlazione rispetto agli ordini dell'articolo principale",
    )


class ProductRecommendationResponse(BaseModel):
    product: ProductResponse
    purchase_frequency: PurchaseFrequency
    bought_together: list[BoughtTogetherItem]


class RecommendationImportResult(BaseModel):
    orders_imported: int
    orders_updated: int
    lines_imported: int
    lines_skipped: int
    recommendations_computed: int
    errors: list[str]


class RecomputeResult(BaseModel):
    products_with_stats: int
    cooccurrence_pairs: int
