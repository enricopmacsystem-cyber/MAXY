from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

AUDITED_PREFIXES = (
    "/api/chat",
    "/api/commercial-copilot",
    "/api/products",
    "/api/recommendations",
    "/api/auth",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logging strutturato per richieste API."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        path = request.url.path

        if not path.startswith("/api"):
            return await call_next(request)

        response = await call_next(request)

        if any(path.startswith(prefix) for prefix in AUDITED_PREFIXES):
            logger.info(
                "API %s %s | status=%s | client=%s",
                request.method,
                path,
                response.status_code,
                request.client.host if request.client else "unknown",
            )

        if settings.auth_required and response.status_code == 401:
            logger.warning("Accesso non autorizzato: %s %s", request.method, path)

        return response
