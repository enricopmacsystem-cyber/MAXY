from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import CalendarUser, DbSession
from app.core.exceptions import CalendarError
from app.schemas.calendar import CalendarStatusResponse, UnifiedCalendarResponse
from app.services.calendar_service import CalendarService

router = APIRouter()


@router.get("/status", response_model=CalendarStatusResponse)
def calendar_status(db: DbSession, user: CalendarUser) -> CalendarStatusResponse:
    service = CalendarService(db)
    user_id = user.user_id if user else "anonymous"
    token = user.easyone_access_token if user else None
    return service.status(easyone_user_id=user_id, easyone_access_token=token)


@router.get("/unified", response_model=UnifiedCalendarResponse)
def unified_calendar(
    db: DbSession,
    user: CalendarUser,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    outlook_account_id: uuid.UUID | None = Query(None),
    include_outlook: bool = Query(True),
    include_easyone: bool = Query(True),
) -> UnifiedCalendarResponse:
    service = CalendarService(db)
    user_id = user.user_id if user else "anonymous"
    token = user.easyone_access_token if user else None
    try:
        return service.unified(
            easyone_user_id=user_id,
            easyone_access_token=token,
            start=start,
            end=end,
            outlook_account_id=outlook_account_id,
            include_outlook=include_outlook,
            include_easyone=include_easyone,
        )
    except CalendarError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
