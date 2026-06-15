from fastapi import APIRouter, HTTPException, Query, Request as HttpRequest

from app.api.dependencies import AiCopilotUser, DbSession, audit_action
from app.core.exceptions import CopilotError
from app.core.logging import get_logger
from app.schemas.commercial_copilot import (
    CommercialCopilotRequest,
    CommercialCopilotResponse,
)
from app.services.commercial_copilot_service import CommercialCopilotService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/analyze", response_model=CommercialCopilotResponse)
def analyze_product(
    payload: CommercialCopilotRequest,
    http_request: HttpRequest,
    db: DbSession,
    user: AiCopilotUser = None,
) -> CommercialCopilotResponse:
    """
    Commercial Copilot: analisi completa articolo da EasyOne + opportunità commerciali.
    """
    service = CommercialCopilotService(db)
    try:
        result = service.analyze(payload)
        if user:
            audit_action(
                db,
                user,
                action="ai.copilot.analyze",
                entity_type="product_query",
                entity_id=payload.query[:100],
                ip_address=http_request.client.host if http_request.client else None,
            )
        return result
    except CopilotError as exc:
        logger.error("Commercial Copilot errore: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/analyze/{query}", response_model=CommercialCopilotResponse)
def analyze_product_get(
    query: str,
    http_request: HttpRequest,
    db: DbSession,
    user: AiCopilotUser = None,
    include_ai_summary: bool = Query(default=True),
    limit_per_section: int = Query(default=5, ge=1, le=20),
) -> CommercialCopilotResponse:
    """Shortcut GET per Commercial Copilot (codice o descrizione)."""
    service = CommercialCopilotService(db)
    copilot_request = CommercialCopilotRequest(
        query=query,
        include_ai_summary=include_ai_summary,
        limit_per_section=limit_per_section,
    )
    try:
        result = service.analyze(copilot_request)
        if user:
            audit_action(
                db,
                user,
                action="ai.copilot.analyze",
                entity_type="product_query",
                entity_id=query[:100],
                ip_address=http_request.client.host if http_request.client else None,
            )
        return result
    except CopilotError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
