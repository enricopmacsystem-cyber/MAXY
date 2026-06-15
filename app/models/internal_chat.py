from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InternalChatMessage(Base):
    __tablename__ = "internal_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[str] = mapped_column(String(80), nullable=False, default="generale")
    sender_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_username: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
