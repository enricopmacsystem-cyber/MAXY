from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.integrations.easyone.http_client import EasyOneHttpClient, get_erp_client


def build_easyone_client(
    settings: Settings | None = None,
    *,
    access_token: str | None = None,
) -> EasyOneHttpClient | None:
    settings = settings or get_settings()
    if settings.easyone_mode not in ("http", "hybrid") or not settings.easyone_base_url:
        return None
    return EasyOneHttpClient(settings, access_token=access_token)


def build_erp_client(
    settings: Settings | None = None,
    *,
    access_token: str | None = None,
) -> EasyOneHttpClient | None:
    settings = settings or get_settings()
    if settings.easyone_mode not in ("http", "hybrid"):
        return None
    if not (settings.erp_base_url or settings.easyone_base_url):
        return None
    return get_erp_client(settings, access_token=access_token)
