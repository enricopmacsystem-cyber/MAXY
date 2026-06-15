from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppRelease(Base):
    __tablename__ = "app_releases"

    version: Mapped[str] = mapped_column(String(20), primary_key=True)
    download_url: Mapped[str] = mapped_column(Text, nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
