from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import AdminUser, AiChatUser, DbSession, ProductsReadUser, audit_action
from app.core.exceptions import ChatCompletionError
from app.schemas.document import (
    DocumentSearchResponse,
    ImportFolderRequest,
    ImportFolderResponse,
    OpenDocumentRequest,
    WebDocumentSearchResponse,
)
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/search", response_model=DocumentSearchResponse)
def search_documents(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=300),
    internal_code: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    user: ProductsReadUser = None,
) -> DocumentSearchResponse:
    service = DocumentService(db)
    result = service.search(
        q,
        internal_code=internal_code,
        doc_type=doc_type,
        limit=limit,
    )
    if user:
        audit_action(db, user, action="documents.search", details={"query": q})
    return result


@router.post("/import-folder", response_model=ImportFolderResponse)
def import_folder(
    payload: ImportFolderRequest,
    db: DbSession,
    user: AdminUser,
) -> ImportFolderResponse:
    service = DocumentIngestionService(db)
    try:
        result = service.import_folder(
            payload.folder_path,
            recursive=payload.recursive,
            index_pdfs=payload.index_pdfs,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_action(
        db,
        user,
        action="documents.import_folder",
        details={"folder": payload.folder_path, "imported": result.get("imported", 0)},
    )
    return ImportFolderResponse(**result)


@router.get("/search-web", response_model=WebDocumentSearchResponse)
def search_documents_web(
    db: DbSession,
    q: str = Query(..., min_length=2, max_length=300),
    user: AiChatUser = None,
) -> WebDocumentSearchResponse:
    service = DocumentService(db)
    try:
        result = service.search_online(q)
    except ChatCompletionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if user:
        audit_action(db, user, action="documents.search_web", details={"query": q})
    return result


@router.post("/open")
def open_document(
    payload: OpenDocumentRequest,
    db: DbSession,
    user: ProductsReadUser = None,
) -> dict:
    service = DocumentService(db)
    path_or_url = service.resolve_open_path(payload)
    if not path_or_url:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    if user:
        audit_action(
            db,
            user,
            action="documents.open",
            entity_id=str(payload.document_id or payload.internal_code),
        )
    return {"opened": path_or_url, "open_in_browser": True}
