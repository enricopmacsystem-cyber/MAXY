from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.chat import AvailabilityInfo, DocumentationInfo
from app.schemas.product import ProductResponse
from app.schemas.recommendation import PurchaseFrequency


class CopilotProductInsight(BaseModel):
    internal_code: str
    description: str
    manufacturer: str
    category: str
    price: Decimal
    availability: int
    margin_percent: Decimal | None = None
    correlation_percent: Decimal | None = None
    reason: str | None = None


class SalesHistoryDetail(PurchaseFrequency):
    last_order_date: date | None = None


class CommercialCopilotResponse(BaseModel):
    mode: str = Field(default="commercial_copilot")
    query: str

    requested_product: ProductResponse
    availability: AvailabilityInfo
    sales_history: SalesHistoryDetail
    documentation: DocumentationInfo

    compatibility: list[CopilotProductInsight] = Field(default_factory=list)
    alternatives: list[CopilotProductInsight] = Field(default_factory=list)
    bought_together: list[CopilotProductInsight] = Field(default_factory=list)
    similar_products: list[CopilotProductInsight] = Field(default_factory=list)
    complementary: list[CopilotProductInsight] = Field(default_factory=list)
    higher_margin_opportunities: list[CopilotProductInsight] = Field(default_factory=list)
    cross_selling_opportunities: list[CopilotProductInsight] = Field(default_factory=list)

    ai_summary: str = ""
    formatted_report: str = ""


class CommercialCopilotRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Codice o descrizione articolo")
    include_ai_summary: bool = Field(default=True)
    limit_per_section: int = Field(default=5, ge=1, le=20)
