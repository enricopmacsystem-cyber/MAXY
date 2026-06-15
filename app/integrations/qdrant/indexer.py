import hashlib
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config.settings import Settings, get_settings
from app.core.exceptions import QdrantIndexingError
from app.core.logging import get_logger
from app.ingestion.chunker import TextChunk
from app.integrations.qdrant.client import get_qdrant_client
from app.integrations.qdrant.collections import ensure_collection

logger = get_logger(__name__)


def _stable_point_id(chunk_id: str) -> str:
    """Genera un UUID deterministico a partire dall'ID del chunk."""
    digest = hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


class QdrantIndexer:
    """Salva chunk testuali e relativi embeddings in Qdrant."""

    def __init__(
        self,
        client: QdrantClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or get_qdrant_client(self.settings)
        self.collection_name = ensure_collection(
            client=self.client,
            settings=self.settings,
        )

    def upsert_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Inserisce o aggiorna i chunk in Qdrant.

        Returns:
            Numero di punti indicizzati.

        Raises:
            QdrantIndexingError: se i dati non sono coerenti o l'upsert fallisce.
        """
        if len(chunks) != len(embeddings):
            raise QdrantIndexingError(
                f"Numero chunk ({len(chunks)}) diverso dagli embeddings "
                f"({len(embeddings)})"
            )

        if not chunks:
            logger.warning("upsert_chunks chiamato senza dati")
            return 0

        points: list[models.PointStruct] = []

        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = _stable_point_id(chunk.chunk_id)
            payload = {
                "chunk_id": chunk.chunk_id,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "content": chunk.content,
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        logger.info(
            "Upsert di %d punti nella collection '%s'",
            len(points),
            self.collection_name,
        )

        try:
            result = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        except Exception as exc:
            raise QdrantIndexingError(
                f"Errore upsert Qdrant per {len(points)} punti: {exc}"
            ) from exc

        status = getattr(result, "status", "unknown")
        logger.info(
            "Upsert completato: %d punti, status=%s",
            len(points),
            status,
        )
        return len(points)
