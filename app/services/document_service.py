from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.integrations.qdrant.retriever import QdrantRetriever, optional_qdrant_retriever
from app.repositories.document_repo import DocumentRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.chat import SourceCitation
from app.integrations.gemini.chat import ChatService
from app.schemas.document import (
    DocumentResponse,
    DocumentSearchResponse,
    OpenDocumentRequest,
    WebDocumentResult,
    WebDocumentSearchResponse,
)


class DocumentService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        retriever: QdrantRetriever | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = DocumentRepository(session)
        self.product_repo = ProductRepository(session)
        self.retriever = (
            retriever
            if retriever is not None
            else optional_qdrant_retriever(settings=self.settings)
        )

    def search(
        self,
        query: str,
        *,
        internal_code: str | None = None,
        doc_type: str | None = None,
        include_pdf_chunks: bool = True,
        limit: int = 20,
    ) -> DocumentSearchResponse:
        self._sync_product_documents(internal_code)
        items, total = self.repo.search(
            query,
            internal_code=internal_code,
            doc_type=doc_type,
            limit=limit,
        )

        pdf_chunks: list[SourceCitation] = []
        if include_pdf_chunks and query.strip() and self.retriever:
            try:
                chunks = self.retriever.search(query, top_k=5)
                pdf_chunks = [
                    SourceCitation(
                        pdf_name=chunk.source_file,
                        page=chunk.page_number,
                        section=chunk.section,
                    )
                    for chunk in chunks
                ]
            except Exception:
                pdf_chunks = []

        return DocumentSearchResponse(
            items=[DocumentResponse.model_validate(item) for item in items],
            pdf_chunks=pdf_chunks,
            total=total,
        )

    def resolve_open_path(self, request: OpenDocumentRequest) -> str | None:
        doc = None
        if request.document_id:
            doc = self.repo.get_by_id(request.document_id)
        elif request.internal_code and request.doc_type:
            items, _ = self.repo.search(
                "",
                internal_code=request.internal_code,
                doc_type=request.doc_type,
                limit=1,
            )
            doc = items[0] if items else None

        if not doc:
            return None
        if doc.file_path and Path(doc.file_path).exists():
            return doc.file_path
        return doc.file_url

    def _sync_product_documents(self, internal_code: str | None) -> None:
        if internal_code:
            products = [self.product_repo.get_by_internal_code(internal_code)]
        else:
            products, _ = self.product_repo.list_products(limit=200, offset=0)

        for product in products:
            if not product:
                continue
            if product.manual_url:
                self.repo.upsert_from_product(
                    internal_code=product.internal_code,
                    doc_type="manual",
                    title=f"Manuale {product.internal_code}",
                    file_url=str(product.manual_url),
                )
            if product.datasheet_url:
                self.repo.upsert_from_product(
                    internal_code=product.internal_code,
                    doc_type="datasheet",
                    title=f"Scheda tecnica {product.internal_code}",
                    file_url=str(product.datasheet_url),
                )
        self.session.commit()

    def search_online(self, query: str) -> WebDocumentSearchResponse:
        chat = ChatService(settings=self.settings)
        payload = chat.search_documents_online(query)
        results = [
            WebDocumentResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                doc_type=item.get("doc_type", "web"),
            )
            for item in payload.get("results", [])
            if item.get("url")
        ]
        return WebDocumentSearchResponse(
            query=query.strip(),
            answer=payload.get("answer", ""),
            results=results,
        )
