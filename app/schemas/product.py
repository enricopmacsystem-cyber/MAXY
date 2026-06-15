from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductBase(BaseModel):
    internal_code: str = Field(..., min_length=1, max_length=50)
    manufacturer: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=200)
    availability: int = Field(default=0, ge=0)
    price: Decimal = Field(..., ge=0)
    manual_url: HttpUrl | None = None
    datasheet_url: HttpUrl | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    manufacturer: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=200)
    availability: int | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    manual_url: HttpUrl | None = None
    datasheet_url: HttpUrl | None = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cost_price: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class ProductSearchResult(ProductResponse):
    rank: float | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


class ProductSearchResponse(BaseModel):
    items: list[ProductSearchResult]
    total: int
    limit: int
    offset: int
    query: str


class ProductImportResult(BaseModel):
    total_rows: int
    imported: int
    updated: int
    skipped: int
    errors: list[str]
