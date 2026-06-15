from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.document import DocumentIndex


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        query: str,
        *,
        internal_code: str | None = None,
        doc_type: str | None = None,
        limit: int = 20,
    ) -> tuple[list[DocumentIndex], int]:
        filters = []
        if query.strip():
            pattern = f"%{query.strip()}%"
            filters.append(
                or_(
                    DocumentIndex.title.ilike(pattern),
                    DocumentIndex.internal_code.ilike(pattern),
                )
            )
        if internal_code:
            filters.append(DocumentIndex.internal_code == internal_code)
        if doc_type:
            filters.append(DocumentIndex.doc_type == doc_type)

        base = select(DocumentIndex)
        if filters:
            from sqlalchemy import and_

            base = base.where(and_(*filters))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.scalar(count_stmt) or 0

        stmt = base.order_by(DocumentIndex.title).limit(limit)
        return list(self.session.scalars(stmt)), total

    def get_by_id(self, document_id: uuid.UUID) -> DocumentIndex | None:
        return self.session.get(DocumentIndex, document_id)

    def upsert_from_product(
        self,
        *,
        internal_code: str,
        doc_type: str,
        title: str,
        file_url: str | None,
    ) -> DocumentIndex | None:
        if not file_url:
            return None
        stmt = select(DocumentIndex).where(
            DocumentIndex.internal_code == internal_code,
            DocumentIndex.doc_type == doc_type,
        )
        existing = self.session.scalar(stmt)
        if existing:
            existing.file_url = file_url
            existing.title = title
            return existing
        entity = DocumentIndex(
            internal_code=internal_code,
            doc_type=doc_type,
            title=title,
            file_url=file_url,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def upsert_from_file(
        self,
        *,
        file_path: Path,
        title: str | None = None,
        internal_code: str | None = None,
        doc_type: str = "file",
    ) -> DocumentIndex:
        path = file_path.resolve()
        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        stmt = select(DocumentIndex).where(DocumentIndex.file_path == str(path))
        existing = self.session.scalar(stmt)
        display_title = title or path.stem
        if existing:
            existing.title = display_title
            existing.file_hash = file_hash
            existing.internal_code = internal_code or existing.internal_code
            existing.doc_type = doc_type
            self.session.flush()
            return existing

        entity = DocumentIndex(
            internal_code=internal_code,
            doc_type=doc_type,
            title=display_title,
            file_path=str(path),
            file_hash=file_hash,
        )
        self.session.add(entity)
        self.session.flush()
        return entity
