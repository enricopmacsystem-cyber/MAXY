from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WhatsAppDraft(Base):
    __tablename__ = "whatsapp_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_sessions.id", ondelete="SET NULL")
    )
    easyone_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(30))
    customer_code: Mapped[str | None] = mapped_column(String(50))
    inbound_message: Mapped[str] = mapped_column(Text, nullable=False)
    draft_reply: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_products: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
