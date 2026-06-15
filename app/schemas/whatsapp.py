from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WhatsAppDraftRequest(BaseModel):
    inbound_message: str = Field(..., min_length=1, max_length=4000)
    customer_phone: str | None = Field(default=None, max_length=30)
    customer_code: str | None = Field(default=None, max_length=50)
    product_context: str | None = Field(
        default=None,
        description="Codice prodotto opzionale per contestualizzare la risposta",
    )
    send_via_api: bool = Field(
        default=False,
        description="Invia direttamente via WhatsApp Business API se configurata",
    )


class WhatsAppDraftResponse(BaseModel):
    id: UUID
    draft_reply: str
    suggested_products: list[str] = Field(default_factory=list)
    customer_code: str | None = None
    created_at: datetime
    sent: bool = False
    send_status: str | None = None
