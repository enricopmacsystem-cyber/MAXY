from __future__ import annotations

import uuid
from datetime import datetime

from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerCache(Base):
    __tablename__ = "customer_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False)
    vat_number: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    address_line: Mapped[str | None] = mapped_column(String(300))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    province: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    sales_agent: Mapped[str | None] = mapped_column(String(100))
    source_system: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
