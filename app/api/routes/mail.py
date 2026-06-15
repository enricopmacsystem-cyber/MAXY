from __future__ import annotations

import uuid
from html import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.api.dependencies import CurrentUser, DbSession, MailUser, audit_action
from app.core.exceptions import MailError
from app.schemas.mail import (
    MailAccountResponse,
    MailMessageDetail,
    MailMessageListResponse,
    MailOAuthStartRequest,
    MailOAuthStartResponse,
    MailOAuthStatusResponse,
    MailProviderStatus,
    MailSendRequest,
    MailSendResponse,
)
from app.services.mail_service import MailService

router = APIRouter()

_OAUTH_SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="it">
<head><meta charset="utf-8"><title>Posta collegata</title></head>
<body style="font-family:Segoe UI,sans-serif;text-align:center;padding:3rem;">
  <h2>Account posta collegato</h2>
  <p>Puoi chiudere questa finestra e tornare a MAC AI Assistant.</p>
</body>
</html>
"""


def _oauth_error_html(title: str, message: str) -> HTMLResponse:
    return HTMLResponse(
        f"<h3>{escape(title)}</h3><p>{escape(message)}</p>",
        status_code=400,
    )


@router.get("/status", response_model=MailProviderStatus)
def mail_provider_status(db: DbSession) -> MailProviderStatus:
    return MailService(db).provider_status()


@router.get("/accounts", response_model=list[MailAccountResponse])
def list_mail_accounts(db: DbSession, user: MailUser) -> list[MailAccountResponse]:
    service = MailService(db)
    user_id = user.user_id if user else "anonymous"
    return service.list_accounts(user_id)


@router.post("/oauth/start", response_model=MailOAuthStartResponse)
def start_mail_oauth(
    payload: MailOAuthStartRequest,
    request: Request,
    db: DbSession,
    user: MailUser,
) -> MailOAuthStartResponse:
    if not user:
        raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    service = MailService(db)
    try:
        result = service.start_oauth(
            easyone_user_id=user.user_id,
            provider=payload.provider,
        )
    except MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_action(
        db,
        user,
        action="mail.oauth.start",
        details={"provider": payload.provider},
        ip_address=request.client.host if request.client else None,
    )
    return result


@router.get("/oauth/status/{state}", response_model=MailOAuthStatusResponse)
def mail_oauth_status(state: str, db: DbSession, user: CurrentUser) -> MailOAuthStatusResponse:
    from app.integrations.mail.oauth_state import get_pending

    entry = get_pending(state)
    if entry and entry.easyone_user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Sessione OAuth non autorizzata")
    return MailService(db).oauth_status(state)


@router.get("/oauth/callback", response_class=HTMLResponse)
def mail_oauth_callback(
    code: str,
    state: str,
    db: DbSession,
    error: str | None = None,
    error_description: str | None = None,
) -> HTMLResponse:
    service = MailService(db)
    if error:
        from app.integrations.mail.oauth_state import mark_error

        mark_error(state, error_description or error)
        return _oauth_error_html("Accesso annullato", error_description or error or "Annullato")
    try:
        email = service.complete_oauth(code=code, state=state)
    except MailError as exc:
        return _oauth_error_html("Errore collegamento", str(exc))
    return HTMLResponse(
        _OAUTH_SUCCESS_HTML.replace("collegato", f"collegato ({escape(email)})"),
        status_code=200,
    )


@router.delete("/accounts/{account_id}")
def disconnect_mail_account(
    account_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: MailUser,
) -> dict[str, str]:
    if not user:
        raise HTTPException(status_code=401, detail="Autenticazione richiesta")
    service = MailService(db)
    try:
        service.disconnect(easyone_user_id=user.user_id, account_id=account_id)
    except MailError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_action(
        db,
        user,
        action="mail.disconnect",
        entity_id=str(account_id),
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "disconnected"}


@router.get("/messages", response_model=MailMessageListResponse)
def list_mail_messages(
    account_id: uuid.UUID,
    db: DbSession,
    user: MailUser,
    limit: int = 50,
    folder: str = "inbox",
) -> MailMessageListResponse:
    service = MailService(db)
    user_id = user.user_id if user else "anonymous"
    try:
        return service.list_messages(
            easyone_user_id=user_id,
            account_id=account_id,
            limit=limit,
            folder=folder,
        )
    except MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/messages/{message_id}", response_model=MailMessageDetail)
def get_mail_message(
    message_id: str,
    account_id: uuid.UUID,
    db: DbSession,
    user: MailUser,
) -> MailMessageDetail:
    service = MailService(db)
    user_id = user.user_id if user else "anonymous"
    try:
        return service.get_message(
            easyone_user_id=user_id,
            account_id=account_id,
            message_id=message_id,
        )
    except MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/send", response_model=MailSendResponse)
def send_mail_message(
    payload: MailSendRequest,
    request: Request,
    db: DbSession,
    user: MailUser,
) -> MailSendResponse:
    service = MailService(db)
    user_id = user.user_id if user else "anonymous"
    try:
        result = service.send_message(easyone_user_id=user_id, payload=payload)
    except MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user:
        audit_action(
            db,
            user,
            action="mail.send",
            details={"to": payload.to, "subject": payload.subject[:120]},
            ip_address=request.client.host if request.client else None,
        )
    return result
