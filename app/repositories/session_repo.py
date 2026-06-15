from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.session import UserSession


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        session_id: uuid.UUID | None = None,
        easyone_user_id: str,
        easyone_username: str,
        display_name: str | None,
        roles: list[str],
        permissions: list[str],
        token_hash: str,
        refresh_token_hash: str,
        expires_at: datetime,
        easyone_access_token: str | None = None,
    ) -> UserSession:
        entity = UserSession(
            id=session_id or uuid.uuid4(),
            easyone_user_id=easyone_user_id,
            easyone_username=easyone_username,
            display_name=display_name,
            roles_json=roles,
            permissions_json=permissions,
            token_hash=token_hash,
            refresh_token_hash=refresh_token_hash,
            easyone_access_token=easyone_access_token,
            expires_at=expires_at,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_by_id(self, session_id: uuid.UUID) -> UserSession | None:
        return self.session.get(UserSession, session_id)

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.token_hash == token_hash)
        return self.session.scalar(stmt)

    def get_by_refresh_hash(self, refresh_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_hash == refresh_hash
        )
        return self.session.scalar(stmt)

    def touch_activity(self, session_id: uuid.UUID) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(last_activity=datetime.now(UTC))
        )
        self.session.execute(stmt)

    def rotate_tokens(
        self,
        session_id: uuid.UUID,
        *,
        token_hash: str,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(
                token_hash=token_hash,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
                last_activity=datetime.now(UTC),
            )
        )
        self.session.execute(stmt)

    def delete_session(self, session_id: uuid.UUID) -> None:
        stmt = delete(UserSession).where(UserSession.id == session_id)
        self.session.execute(stmt)

    def delete_expired(self) -> int:
        stmt = delete(UserSession).where(UserSession.expires_at < datetime.now(UTC))
        result = self.session.execute(stmt)
        return result.rowcount or 0
