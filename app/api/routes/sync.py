from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminSyncUser, DbSession, audit_action
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/orders")
def sync_orders(db: DbSession, user: AdminSyncUser = None) -> dict:
    """Sincronizza ordini da EasyOne/ERP verso cache locale (incrementale)."""
    service = SyncService(db)
    token = user.easyone_access_token if user else None
    result = service.sync_full_from_easyone(easyone_access_token=token)
    if user:
        audit_action(db, user, action="sync.orders", details=result)
    elif result.get("status") == "skipped":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("reason", "Sync non disponibile"),
        )
    return result
