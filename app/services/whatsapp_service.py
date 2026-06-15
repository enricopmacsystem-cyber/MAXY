from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.openai.chat import ChatService
from app.repositories.customer_repo import CustomerRepository
from app.repositories.product_repo import ProductRepository
from app.integrations.whatsapp.client import WhatsAppBusinessClient
from app.repositories.whatsapp_repo import WhatsAppRepository
from app.schemas.whatsapp import WhatsAppDraftRequest, WhatsAppDraftResponse

logger = get_logger(__name__)

def whatsapp_system_prompt(assistant_name: str) -> str:
    return f"""Sei {assistant_name}, assistente commerciale per un distributore tecnologico.
Il tuo nome è sempre Maxy: non dire di essere Gemini, Google, ChatGPT o altro modello.
Genera una bozza di risposta professionale in italiano per WhatsApp Business.
Regole:
- Tono cordiale e conciso (adatto a WhatsApp)
- Non inventare prezzi o giacenze non forniti nel contesto
- Proponi passi chiari (verifica disponibilità, invio preventivo, richiamata)
- Max 6-8 righe
"""


class WhatsAppService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        chat_service: ChatService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = WhatsAppRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
        self.chat = chat_service or ChatService(settings=self.settings)
        self.whatsapp = WhatsAppBusinessClient(settings=self.settings)

    def create_draft(
        self,
        request: WhatsAppDraftRequest,
        *,
        easyone_user_id: str,
        session_id: uuid.UUID | None = None,
    ) -> WhatsAppDraftResponse:
        customer = None
        if request.customer_code:
            customer = self.customer_repo.get_by_code(request.customer_code)
        elif request.customer_phone:
            customer = self.customer_repo.get_by_phone(request.customer_phone)

        product_context = ""
        suggested: list[str] = []
        if request.product_context:
            product = self.product_repo.get_by_internal_code(request.product_context)
            if product:
                product_context = (
                    f"Prodotto: {product.internal_code} - {product.manufacturer} "
                    f"- {product.description} - disp: {product.availability}"
                )
                suggested.append(product.internal_code)

        customer_context = ""
        if customer:
            customer_context = (
                f"Cliente: {customer.company_name} ({customer.customer_code}), "
                f"agente: {customer.sales_agent or 'N/D'}"
            )

        user_prompt = f"""Messaggio cliente:
{request.inbound_message}

Contesto:
{customer_context or 'Cliente non identificato'}
{product_context or 'Nessun prodotto specificato'}

Genera la bozza di risposta WhatsApp."""

        try:
            draft_reply = self.chat.generate_simple_completion(
                system_prompt=whatsapp_system_prompt(self.settings.ai_assistant_name),
                user_prompt=user_prompt,
            )
        except Exception as exc:
            logger.warning("Fallback bozza WhatsApp senza AI: %s", exc)
            draft_reply = (
                "Buongiorno, grazie per il messaggio. "
                "Verifico subito disponibilità e condizioni per lei e le rispondo a breve."
            )

        entity = self.repo.create(
            session_id=session_id,
            easyone_user_id=easyone_user_id,
            customer_phone=request.customer_phone,
            customer_code=customer.customer_code if customer else request.customer_code,
            inbound_message=request.inbound_message,
            draft_reply=draft_reply,
            suggested_products=suggested,
        )
        sent = False
        send_status: str | None = None
        phone = request.customer_phone or (customer.phone if customer else None)
        if request.send_via_api and phone and self.whatsapp.is_configured:
            try:
                self.whatsapp.send_text_message(phone, draft_reply)
                sent = True
                send_status = "sent"
                entity.status = "sent"
            except Exception as exc:
                send_status = f"error: {exc}"
                logger.warning("Invio WhatsApp fallito: %s", exc)

        self.session.commit()

        return WhatsAppDraftResponse(
            id=entity.id,
            draft_reply=entity.draft_reply,
            suggested_products=entity.suggested_products,
            customer_code=entity.customer_code,
            created_at=entity.created_at,
            sent=sent,
            send_status=send_status,
        )
