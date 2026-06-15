from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_code: str
    company_name: str
    vat_number: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    address_line: str | None = None
    postal_code: str | None = None
    province: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    sales_agent: str | None = None
    source_system: str
    fetched_at: datetime


class CustomerSearchResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
