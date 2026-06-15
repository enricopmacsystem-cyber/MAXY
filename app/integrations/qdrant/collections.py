from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def ensure_collection(
    client: QdrantClient,
    collection_name: str | None = None,
    vector_size: int | None = None,
    settings: Settings | None = None,
) -> str:
    """
    Crea la collection Qdrant se non esiste già.

    Returns:
        Nome della collection utilizzata.
    """
    config = settings or get_settings()
    name = collection_name or config.qdrant_collection
    size = vector_size or config.embedding_dimensions

    logger.info(
        "Verifica collection Qdrant '%s' (dimensione vettori=%d)",
        name,
        size,
    )

    try:
        existing = {col.name for col in client.get_collections().collections}
    except Exception as exc:
        logger.error("Impossibile contattare Qdrant: %s", exc)
        raise

    if name in existing:
        logger.info("Collection '%s' già esistente", name)
        return name

    logger.info("Creazione collection '%s'", name)
    client.create_collection(
        collection_name=name,
        vectors_config=models.VectorParams(
            size=size,
            distance=models.Distance.COSINE,
        ),
    )
    logger.info("Collection '%s' creata con successo", name)
    return name
