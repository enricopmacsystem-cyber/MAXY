from decimal import Decimal



from pydantic import BaseModel, Field



from app.schemas.product import ProductResponse

from app.schemas.recommendation import BoughtTogetherItem





class ProductSalesStats(BaseModel):

    product: ProductResponse

    order_count: int

    total_quantity: Decimal

    correlation_top: list[BoughtTogetherItem] = Field(default_factory=list)





class SalesAnalyticsResponse(BaseModel):

    top_products: list[ProductSalesStats]

    total_orders: int

    period_label: str = "storico completo"





class CustomerProductPurchase(BaseModel):

    product: ProductResponse

    brand: str

    total_quantity: Decimal

    order_count: int

    share_percent: Decimal = Field(description="% sul totale acquisti del cliente")

    brand_share_percent: Decimal = Field(description="% all'interno del brand")

    avg_unit_price: Decimal | None = None

    max_discount_percent: Decimal = Decimal("0")

    suggested_discount_percent: Decimal = Decimal("0")





class CustomerBrandBreakdown(BaseModel):

    brand: str

    total_quantity: Decimal

    share_percent: Decimal

    product_count: int

    max_discount_percent: Decimal = Decimal("0")

    suggested_discount_percent: Decimal = Decimal("0")

    products: list[CustomerProductPurchase] = Field(default_factory=list)





class CustomerAnalyticsResponse(BaseModel):

    customer_code: str

    company_name: str | None = None

    city: str | None = None

    sales_agent: str | None = None

    total_orders: int = 0

    total_quantity: Decimal = Decimal("0")

    brands: list[CustomerBrandBreakdown] = Field(default_factory=list)

    source: str = "local"

    warnings: list[str] = Field(default_factory=list)





class CustomerMaxySuggestionItem(BaseModel):

    internal_code: str

    description: str

    brand: str

    reason: str

    correlation_percent: Decimal | None = None





class CustomerMaxySuggestionsResponse(BaseModel):

    customer_code: str

    company_name: str | None = None

    summary: str

    suggestions: list[CustomerMaxySuggestionItem] = Field(default_factory=list)

    cross_sell: list[CustomerMaxySuggestionItem] = Field(default_factory=list)


