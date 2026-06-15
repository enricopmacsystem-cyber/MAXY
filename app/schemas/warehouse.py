from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.chat import AvailabilityInfo
from app.schemas.product import ProductResponse


class WarehouseItem(BaseModel):
    product: ProductResponse
    availability: AvailabilityInfo
    warehouse_code: str = Field(default="MAIN")
    location: str | None = None
    fetched_at: datetime
    source: str = "local"


class WarehouseSearchResponse(BaseModel):
    items: list[WarehouseItem]
    total: int
