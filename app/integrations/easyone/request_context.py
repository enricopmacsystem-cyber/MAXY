from __future__ import annotations

from typing import Any

from app.config.settings import Settings, get_settings


def merge_query_params(
    params: dict[str, Any] | None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Unisce parametri query senza modifiche (tenantId solo nel body di login)."""
    _ = settings
    return dict(params or {})
