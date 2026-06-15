from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MailProviderStatus(BaseModel):
    gmail_configured: bool
    outlook_configured: bool
    redirect_uri: str


class MailAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    email_address: str
    connected_at: datetime


class MailOAuthStartRequest(BaseModel):
    provider: str = Field(..., pattern="^(gmail|outlook)$")


class MailOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class MailOAuthStatusResponse(BaseModel):
    status: str
    email_address: str | None = None
    account_id: uuid.UUID | None = None
    message: str | None = None


class MailMessageSummary(BaseModel):
    id: str
    subject: str
    from_address: str
    from_name: str | None = None
    received_at: datetime | None = None
    snippet: str = ""
    is_read: bool = True


class MailMessageListResponse(BaseModel):
    messages: list[MailMessageSummary]
    total: int


class MailMessageDetail(BaseModel):
    id: str
    subject: str
    from_address: str
    from_name: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    received_at: datetime | None = None
    body_text: str = ""
    body_html: str | None = None
    attachments: list[str] = Field(default_factory=list)


class MailAttachmentInput(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    content_base64: str


class MailSendRequest(BaseModel):
    account_id: uuid.UUID
    to: str
    subject: str
    body: str
    cc: list[str] = Field(default_factory=list)
    attachments: list[MailAttachmentInput] = Field(default_factory=list)
    reply_to_message_id: str | None = None


class MailSendResponse(BaseModel):
    message_id: str | None = None
    status: str = "sent"
