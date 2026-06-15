from fastapi import APIRouter

from app.config.settings import _is_mock_easyone_url, get_settings
from app.db.session import check_database_connection

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    db_ok = check_database_connection()
    status_value = "ok" if db_ok else "degraded"
    easyone_base_url = (settings.easyone_base_url or "").strip()
    return {
        "status": status_value,
        "database": "up" if db_ok else "down",
        "auth_required": settings.auth_required,
        "easyone_auth_mode": settings.easyone_auth_mode,
        "easyone_configured": bool(easyone_base_url) and not _is_mock_easyone_url(easyone_base_url),
        "easyone_api_url": easyone_base_url or None,
        "easyone_mock": _is_mock_easyone_url(easyone_base_url) if easyone_base_url else False,
        "easyone_portal_url": settings.easyone_portal_url or None,
        "easyone_mode": settings.easyone_mode,
        "ai_assistant_name": settings.ai_assistant_name,
        "ai_provider": "gemini",
        "ai_configured": settings.ai_configured,
        "technical_ai_provider": "anthropic",
        "technical_ai_configured": settings.technical_ai_configured,
        "chroma_dir": str(settings.chroma_dir) if settings.chroma_dir else None,
        "version": settings.app_current_version,
    }
