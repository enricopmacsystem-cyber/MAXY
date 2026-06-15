from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.integrations.easyone.adapter import (
    EasyOneAdapter,
    HttpEasyOneAdapter,
    LocalEasyOneAdapter,
)


def get_easyone_adapter(
    session: Session,
    settings: Settings | None = None,
    *,
    access_token: str | None = None,
) -> EasyOneAdapter:
    settings = settings or get_settings()
    if settings.easyone_mode in ("http", "hybrid") and settings.easyone_base_url:
        return HttpEasyOneAdapter(
            session,
            settings=settings,
            access_token=access_token,
        )
    return LocalEasyOneAdapter(session)
