from qdrant_client import QdrantClient

from app.config.settings import Settings, get_settings


def get_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    config = settings or get_settings()
    return QdrantClient(url=config.qdrant_url, prefer_grpc=False)
