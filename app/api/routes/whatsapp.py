from fastapi import APIRouter, Request

from app.api.dependencies import AiChatUser, DbSession, audit_action
from app.schemas.whatsapp import WhatsAppDraftRequest, WhatsAppDraftResponse
from app.services.whatsapp_service import WhatsAppService

router = APIRouter()


@router.post("/draft", response_model=WhatsAppDraftResponse)
def create_whatsapp_draft(
    payload: WhatsAppDraftRequest,
    request: Request,
    db: DbSession,
    user: AiChatUser = None,
) -> WhatsAppDraftResponse:
    service = WhatsAppService(db)
    user_id = user.user_id if user else "anonymous"
    session_id = user.session_id if user else None
    result = service.create_draft(
        payload,
        easyone_user_id=user_id,
        session_id=session_id,
    )
    if user:
        audit_action(
            db,
            user,
            action="whatsapp.draft",
            details={"customer_phone": payload.customer_phone},
            ip_address=request.client.host if request.client else None,
        )
    return result
