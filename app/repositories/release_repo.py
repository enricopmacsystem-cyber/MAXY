from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.release import AppRelease


class ReleaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_latest(self) -> AppRelease | None:
        stmt = select(AppRelease).order_by(AppRelease.published_at.desc()).limit(1)
        return self.session.scalar(stmt)
