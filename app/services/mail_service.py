from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import MailError
from app.core.secrets_at_rest import decrypt_at_rest, encrypt_at_rest
from app.integrations.mail import gmail_client, outlook_client
from app.integrations.mail.oauth import (
    GMAIL_SCOPES,
    OUTLOOK_SCOPES,
    build_authorization_url,
    exchange_code,
    fetch_user_email,
    refresh_access_token,
    token_expires_at,
)
from app.integrations.mail.oauth_state import (
    create_pending,
    get_pending,
    mark_error,
    mark_success,
)
from app.models.mail_account import MailOAuthAccount
from app.repositories.mail_repo import MailAccountRepository
from app.schemas.mail import (
    MailAccountResponse,
    MailMessageDetail,
    MailMessageListResponse,
    MailOAuthStartResponse,
    MailOAuthStatusResponse,
    MailProviderStatus,
    MailSendRequest,
    MailSendResponse,
)


class MailService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = MailAccountRepository(session)

    def provider_status(self) -> MailProviderStatus:
        return MailProviderStatus(
            gmail_configured=self.settings.gmail_oauth_configured,
            outlook_configured=self.settings.microsoft_oauth_configured,
            redirect_uri=self.settings.mail_oauth_redirect_uri,
        )

    def list_accounts(self, easyone_user_id: str) -> list[MailAccountResponse]:
        return [
            MailAccountResponse(
                id=account.id,
                provider=account.provider,
                email_address=account.email_address,
                connected_at=account.created_at,
            )
            for account in self.repo.list_for_user(easyone_user_id)
        ]

    def start_oauth(self, *, easyone_user_id: str, provider: str) -> MailOAuthStartResponse:
        state = create_pending(easyone_user_id=easyone_user_id, provider=provider)
        auth_url = build_authorization_url(self.settings, provider=provider, state=state)
        return MailOAuthStartResponse(authorization_url=auth_url, state=state)

    def oauth_status(self, state: str) -> MailOAuthStatusResponse:
        pending = get_pending(state)
        if not pending:
            return MailOAuthStatusResponse(status="expired", message="Sessione OAuth scaduta.")
        if pending.status == "success":
            return MailOAuthStatusResponse(
                status="success",
                email_address=pending.email_address,
                account_id=uuid.UUID(pending.account_id) if pending.account_id else None,
            )
        if pending.status == "error":
            return MailOAuthStatusResponse(status="error", message=pending.error_message)
        return MailOAuthStatusResponse(status="pending")

    def complete_oauth(self, *, code: str, state: str) -> str:
        pending = get_pending(state)
        if not pending:
            raise MailError("Sessione OAuth non valida o scaduta.")
        try:
            token_payload = exchange_code(
                self.settings,
                provider=pending.provider,
                code=code,
            )
            access_token = str(token_payload.get("access_token", ""))
            if not access_token:
                raise MailError("Token di accesso non ricevuto dal provider.")
            refresh_token = token_payload.get("refresh_token")
            expires = token_expires_at(token_payload)
            email = fetch_user_email(
                self.settings,
                provider=pending.provider,
                access_token=access_token,
            )
            scopes = GMAIL_SCOPES if pending.provider == "gmail" else OUTLOOK_SCOPES
            account = self.repo.upsert_account(
                easyone_user_id=pending.easyone_user_id,
                provider=pending.provider,
                email_address=email,
                access_token=encrypt_at_rest(access_token) or access_token,
                refresh_token=encrypt_at_rest(str(refresh_token)) if refresh_token else None,
                token_expires_at=expires,
                scopes=scopes,
            )
            self.session.commit()
            mark_success(state, email_address=email, account_id=str(account.id))
            return email
        except Exception as exc:
            mark_error(state, str(exc))
            raise

    def disconnect(self, *, easyone_user_id: str, account_id: uuid.UUID) -> None:
        if not self.repo.delete_for_user(account_id, easyone_user_id):
            raise MailError("Account posta non trovato.")
        self.session.commit()

    def list_messages(
        self,
        *,
        easyone_user_id: str,
        account_id: uuid.UUID,
        limit: int = 50,
        folder: str = "inbox",
    ) -> MailMessageListResponse:
        account = self._get_account(account_id, easyone_user_id)
        token = self._ensure_access_token(account)
        if account.provider == "gmail":
            messages = gmail_client.list_messages(token, limit=limit, folder=folder)
        else:
            messages = outlook_client.list_messages(token, limit=limit, folder=folder)
        return MailMessageListResponse(messages=messages, total=len(messages))

    def get_message(
        self,
        *,
        easyone_user_id: str,
        account_id: uuid.UUID,
        message_id: str,
    ) -> MailMessageDetail:
        account = self._get_account(account_id, easyone_user_id)
        token = self._ensure_access_token(account)
        if account.provider == "gmail":
            return gmail_client.get_message(token, message_id)
        return outlook_client.get_message(token, message_id)

    def send_message(self, *, easyone_user_id: str, payload: MailSendRequest) -> MailSendResponse:
        account = self._get_account(payload.account_id, easyone_user_id)
        token = self._ensure_access_token(account)
        if account.provider == "gmail":
            message_id = gmail_client.send_message(
                token,
                to=payload.to,
                subject=payload.subject,
                body=payload.body,
                cc=payload.cc,
                attachments=payload.attachments,
            )
        else:
            message_id = outlook_client.send_message(
                token,
                to=payload.to,
                subject=payload.subject,
                body=payload.body,
                cc=payload.cc,
                attachments=payload.attachments,
            )
        return MailSendResponse(message_id=message_id or None, status="sent")

    def _get_account(self, account_id: uuid.UUID, easyone_user_id: str) -> MailOAuthAccount:
        account = self.repo.get_for_user(account_id, easyone_user_id)
        if not account:
            raise MailError("Account posta non collegato. Accedere con Gmail o Outlook.")
        return account

    def _ensure_access_token(self, account: MailOAuthAccount) -> str:
        access_token = decrypt_at_rest(account.access_token) or ""
        refresh_token = decrypt_at_rest(account.refresh_token)
        expires = account.token_expires_at
        if expires and expires > datetime.now(UTC) + timedelta(minutes=2):
            return access_token
        if not refresh_token:
            return access_token
        payload = refresh_access_token(
            self.settings,
            provider=account.provider,
            refresh_token=refresh_token,
        )
        new_access = str(payload.get("access_token", ""))
        if not new_access:
            raise MailError("Impossibile rinnovare l'accesso alla casella posta.")
        new_refresh = payload.get("refresh_token")
        self.repo.update_tokens(
            account,
            access_token=encrypt_at_rest(new_access) or new_access,
            refresh_token=encrypt_at_rest(str(new_refresh)) if new_refresh else None,
            token_expires_at=token_expires_at(payload),
        )
        self.session.commit()
        return new_access
