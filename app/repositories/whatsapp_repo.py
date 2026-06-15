from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.whatsapp import WhatsAppDraft


class WhatsAppRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        easyone_user_id: str,
        inbound_message: str,
        draft_reply: str,
        session_id: uuid.UUID | None = None,
        customer_phone: str | None = None,
        customer_code: str | None = None,
        suggested_products: list[str] | None = None,
    ) -> WhatsAppDraft:
        entity = WhatsAppDraft(
            session_id=session_id,
            easyone_user_id=easyone_user_id,
            customer_phone=customer_phone,
            customer_code=customer_code,
            inbound_message=inbound_message,
            draft_reply=draft_reply,
            suggested_products=suggested_products or [],
        )
        self.session.add(entity)
        self.session.flush()
        return entity
