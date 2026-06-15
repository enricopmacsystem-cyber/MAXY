from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_ENC_PREFIX = "enc:v1:"


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    digest = hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_at_rest(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith(_ENC_PREFIX):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_at_rest(value: str | None) -> str | None:
    if not value:
        return value
    if not value.startswith(_ENC_PREFIX):
        return value
    try:
        token = value[len(_ENC_PREFIX) :]
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Segreto at-rest non decifrabile (JWT_SECRET_KEY cambiato?)")
        return None
