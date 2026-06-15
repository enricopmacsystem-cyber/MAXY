from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import SourceCitation


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    internal_code: str | None = None
    doc_type: str
    title: str
    file_path: str | None = None
    file_url: str | None = None
    indexed_at: datetime


class DocumentSearchResponse(BaseModel):
    items: list[DocumentResponse]
    pdf_chunks: list[SourceCitation] = Field(default_factory=list)
    total: int


class OpenDocumentRequest(BaseModel):
    document_id: UUID | None = None
    internal_code: str | None = None
    doc_type: str | None = None


class ImportFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    index_pdfs: bool = True


class ImportFolderResponse(BaseModel):
    folder: str
    files_found: int
    imported: int
    pdfs_indexed: int
    errors: list[str] = Field(default_factory=list)


class WebDocumentResult(BaseModel):
    title: str
    url: str
    doc_type: str = "web"


class WebDocumentSearchResponse(BaseModel):
    query: str
    answer: str
    results: list[WebDocumentResult] = Field(default_factory=list)
