from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminUser, DbSession, audit_action
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/orders")
def sync_orders(db: DbSession, user: AdminUser) -> dict:
    """Sincronizza ordini da EasyOne/ERP verso cache locale (incrementale)."""
    service = SyncService(db)
    result = service.sync_full_from_easyone(easyone_access_token=user.easyone_access_token)
    if result.get("status") == "skipped":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("reason", "Sync non disponibile"),
        )
    audit_action(
        db,
        user,
        action="sync.orders",
        details={
            "status": result.get("status"),
            "orders_imported": result.get("orders_imported"),
            "lines_imported": result.get("lines_imported"),
            "errors_count": len(result.get("errors") or []),
        },
    )
    return result
