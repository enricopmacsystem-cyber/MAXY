from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config.settings import Settings, get_settings
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.integrations.gemini.embeddings import EmbeddingService
from app.integrations.qdrant.client import get_qdrant_client
from app.integrations.qdrant.collections import ensure_collection

logger = get_logger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source_file: str
    page_number: int
    section: str
    content: str
    score: float


class QdrantRetriever:
    """Recupera i chunk più rilevanti dalla collection Qdrant."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        embedding_service: EmbeddingService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or get_qdrant_client(self.settings)
        self.embedding_service = embedding_service or EmbeddingService()
        self.collection_name = ensure_collection(
            client=self.client,
            settings=self.settings,
        )

    def search(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        source_file: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Cerca i chunk semanticamente più simili alla domanda dell'utente.

        Raises:
            RetrievalError: se la ricerca in Qdrant fallisce.
        """
        query = query.strip()
        if not query:
            logger.warning("Ricerca RAG con query vuota")
            return []

        limit = top_k or self.settings.rag_top_k
        threshold = (
            score_threshold
            if score_threshold is not None
            else self.settings.rag_score_threshold
        )

        logger.info(
            "Ricerca RAG: top_k=%d, threshold=%.2f, filtro_pdf=%s",
            limit,
            threshold,
            source_file or "nessuno",
        )

        try:
            query_vector = self.embedding_service.embed_texts([query])[0]
        except Exception as exc:
            raise RetrievalError(
                f"Impossibile creare embedding per la query: {exc}"
            ) from exc

        query_filter = None
        if source_file:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="source_file",
                        match=models.MatchValue(value=source_file),
                    )
                ]
            )

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=threshold,
                with_payload=True,
            )
        except Exception as exc:
            raise RetrievalError(f"Errore ricerca Qdrant: {exc}") from exc

        chunks: list[RetrievedChunk] = []
        for hit in results:
            payload = hit.payload or {}
            chunk = RetrievedChunk(
                chunk_id=str(payload.get("chunk_id", hit.id)),
                source_file=str(payload.get("source_file", "sconosciuto.pdf")),
                page_number=int(payload.get("page_number", 0)),
                section=str(payload.get("section", "Generale")),
                content=str(payload.get("content", "")),
                score=float(hit.score or 0.0),
            )
            chunks.append(chunk)
            logger.debug(
                "Chunk recuperato: %s | %s pag.%d | score=%.3f | sezione=%s",
                chunk.chunk_id,
                chunk.source_file,
                chunk.page_number,
                chunk.score,
                chunk.section,
            )

        logger.info("Recuperati %d chunk rilevanti per la query", len(chunks))
        return chunks


def optional_qdrant_retriever(
    settings: Settings | None = None,
    *,
    client: QdrantClient | None = None,
    embedding_service: EmbeddingService | None = None,
) -> QdrantRetriever | None:
    """Crea un retriever Qdrant, o None se il servizio non è raggiungibile."""
    try:
        return QdrantRetriever(
            client=client,
            embedding_service=embedding_service,
            settings=settings,
        )
    except Exception as exc:
        logger.warning(
            "Qdrant non disponibile — ricerca PDF disabilitata: %s",
            exc,
        )
        return None
