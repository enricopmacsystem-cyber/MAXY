from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    cache_key: Mapped[str] = mapped_column(String(500), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
