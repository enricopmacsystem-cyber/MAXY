from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import AiChatUser, DbSession, audit_action
from app.core.exceptions import RAGError
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest, CommercialAssistantResponse
from app.services.chat_service import ConversationService
from app.services.technical_assistant_service import TechnicalAssistantService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/ask", response_model=CommercialAssistantResponse)
def ask_question(
    payload: ChatRequest,
    request: Request,
    db: DbSession,
    user: AiChatUser = None,
) -> CommercialAssistantResponse:
    """
    Assistente commerciale: catalogo, PDF, disponibilità, compatibilità e suggerimenti.
    """
    logger.info("POST /chat/ask | domanda=%s", payload.question[:120])

    try:
        if payload.mode == "technical":
            service = TechnicalAssistantService()
            result = service.ask(payload.question, payload.history)
            audit_action_name = "ai.chat.technical"
        else:
            service = ConversationService(db)
            result = service.chat(
                question=payload.question,
                source_file=payload.source_file,
                top_k=payload.top_k,
            )
            audit_action_name = "ai.chat.ask"

        if user:
            audit_action(
                db,
                user,
                action=audit_action_name,
                details={
                    "question": payload.question[:200],
                    "mode": payload.mode,
                },
                ip_address=request.client.host if request.client else None,
            )
        return result
    except RAGError as exc:
        logger.error("Errore assistente commerciale: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Errore imprevisto assistente commerciale")
        raise HTTPException(
            status_code=502,
            detail="Servizio AI temporaneamente non disponibile.",
        ) from exc
