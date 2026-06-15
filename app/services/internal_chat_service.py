from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.internal_chat_repo import InternalChatRepository
from app.schemas.internal_chat import (
    InternalChatMessageCreate,
    InternalChatMessageListResponse,
    InternalChatMessageResponse,
)
from app.services.auth_service import AuthenticatedUser


class InternalChatService:
    DEFAULT_CHANNEL = "generale"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = InternalChatRepository(session)

    def list_messages(
        self,
        *,
        user: AuthenticatedUser,
        channel: str | None = None,
        limit: int = 100,
        since: datetime | None = None,
    ) -> InternalChatMessageListResponse:
        channel_name = (channel or self.DEFAULT_CHANNEL).strip() or self.DEFAULT_CHANNEL
        items, total = self.repo.list_messages(channel_name, limit=limit, since=since)
        return InternalChatMessageListResponse(
            channel=channel_name,
            items=[self._to_response(item, user) for item in items],
            total=total,
        )

    def send_message(
        self,
        payload: InternalChatMessageCreate,
        *,
        user: AuthenticatedUser,
    ) -> InternalChatMessageResponse:
        channel = (payload.channel or self.DEFAULT_CHANNEL).strip() or self.DEFAULT_CHANNEL
        body = payload.body.strip()
        if not body:
            raise ValueError("Il messaggio non può essere vuoto")

        message = self.repo.create(
            channel=channel,
            sender_user_id=user.user_id,
            sender_username=user.username,
            sender_display_name=user.display_name or user.username,
            body=body,
        )
        self.session.commit()
        return self._to_response(message, user)

    @staticmethod
    def _to_response(
        message,
        user: AuthenticatedUser,
    ) -> InternalChatMessageResponse:
        return InternalChatMessageResponse(
            id=message.id,
            channel=message.channel,
            sender_user_id=message.sender_user_id,
            sender_username=message.sender_username,
            sender_display_name=message.sender_display_name,
            body=message.body,
            created_at=message.created_at,
            is_mine=message.sender_user_id == user.user_id,
        )
