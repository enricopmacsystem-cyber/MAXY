from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    easyone_user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    easyone_username: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    roles_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    permissions_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64))
    easyone_access_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
