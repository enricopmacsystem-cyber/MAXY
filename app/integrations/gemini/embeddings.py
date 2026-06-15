from __future__ import annotations

from google.genai import types

from app.config.settings import Settings, get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.integrations.gemini.client import get_gemini_client

logger = get_logger(__name__)


class EmbeddingService:
    """Crea embeddings testuali tramite Google Gemini API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = get_gemini_client(self.settings)
        self.model = self.settings.gemini_embedding_model
        self.batch_size = self.settings.embedding_batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            logger.warning("embed_texts chiamato con lista vuota")
            return []

        all_embeddings: list[list[float]] = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        logger.info(
            "Creazione embeddings Gemini per %d testi in %d batch (modello=%s)",
            len(texts),
            total_batches,
            self.model,
        )

        for batch_index in range(total_batches):
            start = batch_index * self.batch_size
            end = start + self.batch_size
            batch = texts[start:end]

            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                    ),
                )
            except Exception as exc:
                raise EmbeddingError(
                    f"Errore embedding Gemini al batch {batch_index + 1}: {exc}"
                ) from exc

            vectors = response.embeddings or []
            batch_embeddings = [list(item.values) for item in vectors]

            if len(batch_embeddings) != len(batch):
                raise EmbeddingError(
                    f"Numero embeddings ({len(batch_embeddings)}) diverso "
                    f"dal numero di testi ({len(batch)}) al batch {batch_index + 1}"
                )

            all_embeddings.extend(batch_embeddings)

        logger.info("Creati %d embeddings Gemini con successo", len(all_embeddings))
        return all_embeddings
