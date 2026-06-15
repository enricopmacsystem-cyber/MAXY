from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    id: str
    source: str
    title: str
    start_at: datetime
    end_at: datetime | None = None
    location: str | None = None
    description: str | None = None
    customer: str | None = None
    all_day: bool = False
    color: str = "#4A90D9"


class UnifiedCalendarResponse(BaseModel):
    start: datetime
    end: datetime
    events: list[CalendarEvent]
    outlook_count: int = 0
    easyone_count: int = 0
    outlook_connected: bool = False
    easyone_connected: bool = False
    warnings: list[str] = Field(default_factory=list)


class CalendarStatusResponse(BaseModel):
    easyone_configured: bool
    easyone_connected: bool = False
    easyone_portal_url: str | None = None
    outlook_configured: bool = False
    outlook_account_available: bool
    outlook_account_id: uuid.UUID | None = None
    outlook_email: str | None = None
    needs_outlook_reconnect: bool = False
