from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass


@dataclass
class OAuthPending:
    easyone_user_id: str
    provider: str
    created_at: float
    status: str = "pending"
    email_address: str | None = None
    account_id: str | None = None
    error_message: str | None = None


_lock = threading.Lock()
_pending: dict[str, OAuthPending] = {}
_TTL_SECONDS = 600


def create_pending(*, easyone_user_id: str, provider: str) -> str:
    state = secrets.token_urlsafe(24)
    with _lock:
        _purge_expired()
        _pending[state] = OAuthPending(
            easyone_user_id=easyone_user_id,
            provider=provider,
            created_at=time.time(),
        )
    return state


def get_pending(state: str) -> OAuthPending | None:
    with _lock:
        _purge_expired()
        return _pending.get(state)


def mark_success(state: str, *, email_address: str, account_id: str) -> None:
    with _lock:
        entry = _pending.get(state)
        if entry:
            entry.status = "success"
            entry.email_address = email_address
            entry.account_id = account_id


def mark_error(state: str, message: str) -> None:
    with _lock:
        entry = _pending.get(state)
        if entry:
            entry.status = "error"
            entry.error_message = message


def _purge_expired() -> None:
    now = time.time()
    expired = [key for key, val in _pending.items() if now - val.created_at > _TTL_SECONDS]
    for key in expired:
        _pending.pop(key, None)
