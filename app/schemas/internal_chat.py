from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InternalChatMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    channel: str = Field(default="generale", max_length=80)


class InternalChatMessageResponse(BaseModel):
    id: uuid.UUID
    channel: str
    sender_user_id: str
    sender_username: str
    sender_display_name: str
    body: str
    created_at: datetime
    is_mine: bool = False


class InternalChatMessageListResponse(BaseModel):
    channel: str
    items: list[InternalChatMessageResponse]
    total: int
