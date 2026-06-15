from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.core.exceptions import RAGError
from app.core.logging import get_logger
from app.integrations.macsystem_bot.adapter import (
    TechnicalAssistantAdapter,
    TechnicalChatMessage,
)
from app.schemas.chat import (
    ChatHistoryMessage,
    CommercialAssistantResponse,
    DocumentationInfo,
)

logger = get_logger(__name__)


class TechnicalAssistantService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._adapter = TechnicalAssistantAdapter(self.settings)

    def ask(
        self,
        question: str,
        history: list[ChatHistoryMessage] | None = None,
    ) -> CommercialAssistantResponse:
        question = question.strip()
        if not question:
            raise RAGError("La domanda non può essere vuota")

        if not self._adapter.is_configured():
            raise RAGError(
                "Assistente tecnico non configurato: impostare ANTHROPIC_API_KEY in hub.env"
            )

        if not self._adapter.chroma_ready():
            logger.warning("ChromaDB manuali vuoto o non raggiungibile")
            raise RAGError(
                "Indice manuali tecnici non disponibile. "
                "Verificare CHROMA_DIR e l'accesso alle share di rete."
            )

        messages = [
            TechnicalChatMessage(role=msg.role, content=msg.content)
            for msg in (history or [])
        ]
        result = self._adapter.ask(question, messages)

        return CommercialAssistantResponse(
            answer=result.answer,
            mode="technical",
            technical_sources=result.sources,
            technical_found=result.found,
            documentation=DocumentationInfo(),
        )
