from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.schemas.chat import CommercialAssistantResponse
from app.services.commercial_assistant_service import CommercialAssistantService

logger = get_logger(__name__)


class ConversationService:
    """Facade per l'assistente commerciale esposto all'API."""

    def __init__(self, session: Session) -> None:
        self.commercial_assistant = CommercialAssistantService(session)

    def chat(
        self,
        question: str,
        source_file: str | None = None,
        top_k: int | None = None,
    ) -> CommercialAssistantResponse:
        logger.info("Richiesta assistente commerciale ricevuta")
        return self.commercial_assistant.ask(
            question=question,
            source_file=source_file,
            top_k=top_k,
        )
