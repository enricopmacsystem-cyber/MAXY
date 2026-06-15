from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import DbSession, ProductsReadUser, audit_action
from app.schemas.warehouse import WarehouseItem, WarehouseSearchResponse
from app.services.warehouse_service import WarehouseService

router = APIRouter()


@router.get("/search", response_model=WarehouseSearchResponse)
def search_stock(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    user: ProductsReadUser = None,
) -> WarehouseSearchResponse:
    service = WarehouseService(db)
    token = user.easyone_access_token if user else None
    result = service.search(q, limit=limit, easyone_access_token=token)
    if user:
        audit_action(db, user, action="warehouse.search", details={"query": q})
    return result


@router.get("/{internal_code}", response_model=WarehouseItem)
def get_stock(
    internal_code: str,
    db: DbSession,
    user: ProductsReadUser = None,
) -> WarehouseItem:
    service = WarehouseService(db)
    token = user.easyone_access_token if user else None
    item = service.get_stock(internal_code, easyone_access_token=token)
    if not item:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    if user:
        audit_action(
            db, user, action="warehouse.read", entity_id=internal_code
        )
    return item
