from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log(
        self,
        *,
        easyone_user_id: str,
        action: str,
        session_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            session_id=session_id,
            easyone_user_id=easyone_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        self.session.add(entry)
        self.session.flush()
        return entry
