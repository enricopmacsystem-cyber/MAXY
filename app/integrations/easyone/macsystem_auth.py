"""Autenticazione EasyOne CRM — formato MAC SYSTEM (Bot Ticket)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config.settings import Settings, get_settings
from app.core.exceptions import AuthenticationError


def macsystem_login_payload(
    username: str,
    password: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    tenant_id = (settings.easyone_tenant_id or "").strip()
    if not tenant_id:
        raise AuthenticationError(
            "EASYONE_TENANT_ID non configurato (GUID tenant organizzazione)"
        )
    return {
        "username": username,
        "password": password,
        "tenantId": tenant_id,
        "loginType": 0,
    }


def extract_bearer_token(response: httpx.Response) -> str:
    """
    EasyOne MAC SYSTEM restituisce il token come stringa raw (spesso tra virgolette).
    Allineato a bot_ticket/easyone_client.py.
    """
    raw = response.text.strip()
    if not raw:
        raise AuthenticationError("Risposta login EasyOne vuota")

    plain = raw.strip('"').strip()
    if plain and not plain.startswith("{"):
        return plain

    try:
        parsed = response.json()
    except json.JSONDecodeError:
        if plain:
            return plain
        raise AuthenticationError("Token Bearer non presente nella risposta EasyOne") from None

    if isinstance(parsed, str) and parsed.strip():
        return parsed.strip()
    if isinstance(parsed, dict):
        for key in ("token", "Token", "access_token", "accessToken", "jwt"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    raise AuthenticationError("Token Bearer non presente nella risposta EasyOne")
