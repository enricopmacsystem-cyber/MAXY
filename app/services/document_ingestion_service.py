from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger
from app.ingestion.chunker import chunk_pages
from app.integrations.gemini.embeddings import EmbeddingService
from app.integrations.qdrant.indexer import QdrantIndexer
from app.repositories.document_repo import DocumentRepository
from app.utils.pdf_parser import extract_text_from_pdf

logger = get_logger(__name__)

_SUPPORTED_SUFFIXES = {".pdf", ".PDF"}
_CODE_IN_NAME = re.compile(r"\b([A-Z]{2,}[-_]?[A-Z0-9]{2,})\b")


class DocumentIngestionService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = DocumentRepository(session)

    def import_folder(
        self,
        folder_path: str,
        *,
        recursive: bool = True,
        index_pdfs: bool = True,
    ) -> dict:
        root = Path(folder_path.strip().strip('"'))
        if not root.exists():
            raise FileNotFoundError(f"Percorso non trovato: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Non è una cartella: {root}")

        pattern = "**/*" if recursive else "*"
        files = [
            path
            for path in root.glob(pattern)
            if path.is_file() and path.suffix.lower() in {s.lower() for s in _SUPPORTED_SUFFIXES}
        ]

        imported = 0
        indexed = 0
        errors: list[str] = []

        for file_path in files:
            try:
                code_match = _CODE_IN_NAME.search(file_path.stem)
                internal_code = code_match.group(1) if code_match else None
                doc_type = "manual" if "man" in file_path.stem.lower() else "datasheet"
                self.repo.upsert_from_file(
                    file_path=file_path,
                    internal_code=internal_code,
                    doc_type=doc_type,
                )
                imported += 1
                if index_pdfs and file_path.suffix.lower() == ".pdf":
                    if self._index_pdf(file_path):
                        indexed += 1
            except Exception as exc:
                errors.append(f"{file_path.name}: {exc}")

        self.session.commit()
        return {
            "folder": str(root),
            "files_found": len(files),
            "imported": imported,
            "pdfs_indexed": indexed,
            "errors": errors[:15],
        }

    def _index_pdf(self, pdf_path: Path) -> bool:
        try:
            pages = extract_text_from_pdf(pdf_path)
            if not pages:
                return False
            chunks = chunk_pages(pdf_path, pages)
            if not chunks:
                return False
            embedder = EmbeddingService(self.settings)
            vectors = embedder.embed_texts([chunk.content for chunk in chunks])
            indexer = QdrantIndexer(settings=self.settings)
            indexer.upsert_chunks(chunks, vectors)
            return True
        except Exception as exc:
            logger.warning("Indicizzazione PDF %s non riuscita: %s", pdf_path, exc)
            return False
