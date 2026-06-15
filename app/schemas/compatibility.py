from pydantic import BaseModel, Field

from app.models.compatibility import CompatibilityType
from app.schemas.product import ProductResponse


class RelatedProductResponse(BaseModel):
    product: ProductResponse
    notes: str | None = None
    sort_order: int = 0


class ProductCompatibilityBundle(BaseModel):
    accessories: list[RelatedProductResponse] = Field(default_factory=list)
    alternatives: list[RelatedProductResponse] = Field(default_factory=list)
    spare_parts: list[RelatedProductResponse] = Field(default_factory=list)
    complementary: list[RelatedProductResponse] = Field(default_factory=list)


class ProductDetailResponse(BaseModel):
    product: ProductResponse
    compatibility: ProductCompatibilityBundle


class ProductSearchResultWithCompatibility(BaseModel):
    product: ProductResponse
    rank: float | None = None
    compatibility: ProductCompatibilityBundle


class ProductSearchWithCompatibilityResponse(BaseModel):
    items: list[ProductSearchResultWithCompatibility]
    total: int
    limit: int
    offset: int
    query: str


class CompatibilityLinkCreate(BaseModel):
    related_internal_code: str = Field(..., min_length=1, max_length=50)
    compatibility_type: CompatibilityType
    notes: str | None = None
    sort_order: int = Field(default=0, ge=0)


class CompatibilityLinkResponse(BaseModel):
    id: str
    product_code: str
    related_product_code: str
    compatibility_type: CompatibilityType
    notes: str | None
    sort_order: int
