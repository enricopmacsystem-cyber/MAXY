from dataclasses import dataclass

from app.config.settings import Settings, get_settings
from app.core.exceptions import RAGError, RetrievalError, ChatCompletionError
from app.core.logging import get_logger
from app.integrations.openai.chat import ChatService
from app.integrations.qdrant.retriever import (
    QdrantRetriever,
    RetrievedChunk,
    optional_qdrant_retriever,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    sources: list[dict]
    chunks_used: list[RetrievedChunk]


class RAGService:
    """
    Orchestrazione completa della chat RAG:
    1. Ricerca semantica in Qdrant
    2. Recupero chunk rilevanti
    3. Generazione risposta GPT basata solo sui documenti
    """

    def __init__(
        self,
        retriever: QdrantRetriever | None = None,
        chat_service: ChatService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.retriever = (
            retriever
            if retriever is not None
            else optional_qdrant_retriever(settings=self.settings)
        )
        self.chat_service = chat_service or ChatService(settings=self.settings)

    def ask(
        self,
        question: str,
        source_file: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Risponde a una domanda usando esclusivamente i documenti indicizzati.

        Raises:
            RAGError: se retrieval o generazione falliscono.
        """
        question = question.strip()
        if not question:
            raise RAGError("La domanda non può essere vuota")

        logger.info("Nuova domanda RAG: %s", question[:200])

        if not self.retriever:
            raise RAGError(
                "Servizio documenti non disponibile: Qdrant non è in esecuzione."
            )

        try:
            chunks = self.retriever.search(
                query=question,
                top_k=top_k,
                source_file=source_file,
            )
        except RetrievalError as exc:
            logger.error("Errore retrieval RAG: %s", exc)
            raise RAGError(str(exc)) from exc

        if not chunks:
            logger.warning("Nessun chunk rilevante trovato per la domanda")
            return RAGResponse(
                answer=(
                    "Non ho trovato informazioni sufficienti nei documenti indicizzati "
                    "per rispondere a questa domanda."
                ),
                sources=[],
                chunks_used=[],
            )

        try:
            result = self.chat_service.generate_rag_answer(
                question=question,
                chunks=chunks,
            )
        except ChatCompletionError as exc:
            logger.error("Errore generazione GPT: %s", exc)
            raise RAGError(str(exc)) from exc

        sources = result["sources"]
        logger.info(
            "Risposta RAG pronta: %d fonti citate, %d chunk usati",
            len(sources),
            len(chunks),
        )

        return RAGResponse(
            answer=result["answer"],
            sources=sources,
            chunks_used=chunks,
        )
