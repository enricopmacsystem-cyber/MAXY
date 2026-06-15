from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.compatibility import ProductCompatibilityBundle
from app.schemas.product import ProductResponse


class SourceCitation(BaseModel):
    pdf_name: str = Field(..., description="Nome del file PDF")
    page: int = Field(..., ge=1, description="Numero di pagina")
    section: str = Field(..., description="Titolo della sezione nel PDF")


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    mode: Literal["commercial", "technical"] = Field(
        default="commercial",
        description="commercial = catalogo/magazzino (Gemini); technical = manuali tecnici (Claude)",
    )
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        description="Storia conversazione (usata in modalità technical)",
    )
    source_file: str | None = Field(
        default=None,
        description="Filtra la ricerca PDF su un singolo file (opzionale)",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Numero massimo di chunk PDF da recuperare",
    )


class ArticleInfo(BaseModel):
    internal_code: str
    manufacturer: str
    category: str
    price: Decimal


class AvailabilityInfo(BaseModel):
    quantity: int
    status: str = Field(..., description="disponibile | scorte_basse | esaurito")
    status_label: str = Field(..., description="Etichetta in italiano per il personale")


class DocumentationInfo(BaseModel):
    manual_url: str | None = None
    datasheet_url: str | None = None
    pdf_sources: list[SourceCitation] = Field(default_factory=list)
    technical_summary: str = Field(
        default="",
        description="Sintesi tecnica dai PDF (solo da documenti indicizzati)",
    )


class CommercialSuggestionItem(BaseModel):
    internal_code: str
    description: str
    manufacturer: str
    price: Decimal
    availability: int
    reason: str
    correlation_percent: Decimal | None = None


class CommercialAssistantResponse(BaseModel):
    answer: str = Field(..., description="Risposta operativa per commerciale/magazzino")
    mode: Literal["commercial", "technical"] = "commercial"
    technical_sources: list[str] = Field(
        default_factory=list,
        description="Fonti PDF/manuali (modalità technical)",
    )
    technical_found: bool | None = Field(
        default=None,
        description="True se il motore tecnico ha trovato contesto nei manuali",
    )
    article: ArticleInfo | None = None
    availability: AvailabilityInfo | None = None
    description: str | None = None
    documentation: DocumentationInfo
    compatibility: ProductCompatibilityBundle | None = None
    commercial_suggestions: list[CommercialSuggestionItem] = Field(default_factory=list)
    catalog_matches: int = 0
    pdf_chunks_found: int = 0


# Retrocompatibilità
class ChatResponse(CommercialAssistantResponse):
    pass
