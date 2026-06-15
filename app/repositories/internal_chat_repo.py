from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.internal_chat import InternalChatMessage


class InternalChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_messages(
        self,
        channel: str,
        *,
        limit: int = 100,
        since: datetime | None = None,
    ) -> tuple[list[InternalChatMessage], int]:
        channel_filter = InternalChatMessage.channel == channel
        total = int(
            self.session.scalar(
                select(func.count()).select_from(InternalChatMessage).where(channel_filter)
            )
            or 0
        )

        if since is not None:
            stmt = (
                select(InternalChatMessage)
                .where(channel_filter, InternalChatMessage.created_at > since)
                .order_by(InternalChatMessage.created_at.asc())
                .limit(limit)
            )
            return list(self.session.scalars(stmt)), total

        stmt = (
            select(InternalChatMessage)
            .where(channel_filter)
            .order_by(InternalChatMessage.created_at.desc())
            .limit(limit)
        )
        items = list(reversed(list(self.session.scalars(stmt))))
        return items, total

    def create(
        self,
        *,
        channel: str,
        sender_user_id: str,
        sender_username: str,
        sender_display_name: str,
        body: str,
    ) -> InternalChatMessage:
        message = InternalChatMessage(
            id=uuid.uuid4(),
            channel=channel,
            sender_user_id=sender_user_id,
            sender_username=sender_username,
            sender_display_name=sender_display_name,
            body=body.strip(),
        )
        self.session.add(message)
        self.session.flush()
        return message
