from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config.settings import Settings
from app.core.exceptions import MailError

GMAIL_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/userinfo.email"
)
OUTLOOK_SCOPES = (
    "offline_access Mail.Read Mail.Send User.Read Calendars.Read"
)


def build_authorization_url(settings: Settings, *, provider: str, state: str) -> str:
    redirect_uri = settings.mail_oauth_redirect_uri
    if provider == "gmail":
        if not settings.gmail_oauth_configured:
            raise MailError(
                "Gmail non configurato. Impostare GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET in hub.env."
            )
        params = {
            "client_id": settings.gmail_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    if provider == "outlook":
        if not settings.microsoft_oauth_configured:
            raise MailError(
                "Outlook non configurato. Impostare MICROSOFT_CLIENT_ID e "
                "MICROSOFT_CLIENT_SECRET in hub.env."
            )
        params = {
            "client_id": settings.microsoft_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": OUTLOOK_SCOPES,
            "state": state,
        }
        tenant = settings.microsoft_tenant_id or "common"
        return (
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
            f"{urlencode(params)}"
        )

    raise MailError(f"Provider posta non supportato: {provider}")


def exchange_code(
    settings: Settings,
    *,
    provider: str,
    code: str,
) -> dict:
    redirect_uri = settings.mail_oauth_redirect_uri
    if provider == "gmail":
        data = {
            "code": code,
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        token_url = "https://oauth2.googleapis.com/token"
    elif provider == "outlook":
        tenant = settings.microsoft_tenant_id or "common"
        data = {
            "code": code,
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    else:
        raise MailError(f"Provider posta non supportato: {provider}")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(token_url, data=data)
    if response.status_code >= 400:
        raise MailError(f"Scambio token OAuth fallito: {response.text[:300]}")
    return response.json()


def refresh_access_token(
    settings: Settings,
    *,
    provider: str,
    refresh_token: str,
) -> dict:
    if provider == "gmail":
        data = {
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        token_url = "https://oauth2.googleapis.com/token"
    elif provider == "outlook":
        tenant = settings.microsoft_tenant_id or "common"
        data = {
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": OUTLOOK_SCOPES,
        }
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    else:
        raise MailError(f"Provider posta non supportato: {provider}")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(token_url, data=data)
    if response.status_code >= 400:
        raise MailError(f"Rinnovo token OAuth fallito: {response.text[:300]}")
    return response.json()


def token_expires_at(payload: dict) -> datetime | None:
    expires_in = payload.get("expires_in")
    if not expires_in:
        return None
    return datetime.now(UTC) + timedelta(seconds=int(expires_in))


def fetch_user_email(settings: Settings, *, provider: str, access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=20.0) as client:
        if provider == "gmail":
            response = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers,
            )
        else:
            response = client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    if response.status_code >= 400:
        raise MailError("Impossibile recuperare l'indirizzo email dell'account collegato.")
    data = response.json()
    if provider == "gmail":
        email = data.get("email")
    else:
        email = data.get("mail") or data.get("userPrincipalName")
    if not email:
        raise MailError("Email non disponibile dal provider OAuth.")
    return str(email)
