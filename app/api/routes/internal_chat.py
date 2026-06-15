from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import CurrentUser, DbSession, audit_action
from app.schemas.internal_chat import (
    InternalChatMessageCreate,
    InternalChatMessageListResponse,
    InternalChatMessageResponse,
)
from app.services.internal_chat_service import InternalChatService

router = APIRouter()


@router.get("/messages", response_model=InternalChatMessageListResponse)
def list_messages(
    db: DbSession,
    user: CurrentUser,
    channel: str = Query(default="generale", max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
    since: datetime | None = Query(default=None),
) -> InternalChatMessageListResponse:
    """Elenco messaggi chat interna (canale team)."""
    service = InternalChatService(db)
    result = service.list_messages(
        user=user,
        channel=channel,
        limit=limit,
        since=since,
    )
    audit_action(
        db,
        user,
        action="internal_chat.list",
        details={"channel": channel, "count": len(result.items)},
    )
    return result


@router.post("/messages", response_model=InternalChatMessageResponse)
def send_message(
    payload: InternalChatMessageCreate,
    db: DbSession,
    user: CurrentUser,
) -> InternalChatMessageResponse:
    """Invia un messaggio alla chat interna."""
    service = InternalChatService(db)
    try:
        message = service.send_message(payload, user=user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit_action(
        db,
        user,
        action="internal_chat.send",
        details={"channel": message.channel, "message_id": str(message.id)},
    )
    return message
