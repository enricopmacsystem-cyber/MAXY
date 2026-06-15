from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config.settings import get_settings


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(
    *,
    session_id: uuid.UUID,
    easyone_user_id: str,
    username: str,
    roles: list[str],
    permissions: list[str],
    expires_minutes: int | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(
        minutes=expires_minutes or settings.jwt_access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": easyone_user_id,
        "sid": str(session_id),
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
