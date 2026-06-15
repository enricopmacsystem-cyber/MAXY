from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.mail_account import MailOAuthAccount


class MailAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, easyone_user_id: str) -> list[MailOAuthAccount]:
        stmt = (
            select(MailOAuthAccount)
            .where(MailOAuthAccount.easyone_user_id == easyone_user_id)
            .order_by(MailOAuthAccount.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_for_user(self, account_id: uuid.UUID, easyone_user_id: str) -> MailOAuthAccount | None:
        stmt = select(MailOAuthAccount).where(
            MailOAuthAccount.id == account_id,
            MailOAuthAccount.easyone_user_id == easyone_user_id,
        )
        return self.session.scalar(stmt)

    def upsert_account(
        self,
        *,
        easyone_user_id: str,
        provider: str,
        email_address: str,
        access_token: str,
        refresh_token: str | None,
        token_expires_at: datetime | None,
        scopes: str | None,
    ) -> MailOAuthAccount:
        stmt = select(MailOAuthAccount).where(
            MailOAuthAccount.easyone_user_id == easyone_user_id,
            MailOAuthAccount.provider == provider,
            MailOAuthAccount.email_address == email_address,
        )
        entity = self.session.scalar(stmt)
        now = datetime.now(UTC)
        if entity:
            entity.access_token = access_token
            entity.refresh_token = refresh_token or entity.refresh_token
            entity.token_expires_at = token_expires_at
            entity.scopes = scopes
            entity.updated_at = now
        else:
            entity = MailOAuthAccount(
                easyone_user_id=easyone_user_id,
                provider=provider,
                email_address=email_address,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                scopes=scopes,
                updated_at=now,
            )
            self.session.add(entity)
        self.session.flush()
        return entity

    def update_tokens(
        self,
        account: MailOAuthAccount,
        *,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
    ) -> MailOAuthAccount:
        account.access_token = access_token
        if refresh_token:
            account.refresh_token = refresh_token
        if token_expires_at:
            account.token_expires_at = token_expires_at
        account.updated_at = datetime.now(UTC)
        self.session.flush()
        return account

    def delete_for_user(self, account_id: uuid.UUID, easyone_user_id: str) -> bool:
        stmt = delete(MailOAuthAccount).where(
            MailOAuthAccount.id == account_id,
            MailOAuthAccount.easyone_user_id == easyone_user_id,
        )
        result = self.session.execute(stmt)
        return bool(result.rowcount)
