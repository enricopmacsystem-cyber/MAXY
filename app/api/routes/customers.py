from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import DbSession, ProductsReadUser, audit_action
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerResponse, CustomerSearchResponse

router = APIRouter()


@router.get("/list", response_model=CustomerSearchResponse)
def list_customers(
    db: DbSession,
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=2000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    user: ProductsReadUser = None,
) -> CustomerSearchResponse:
    """Elenco clienti in archivio locale (persistente dopo sync)."""
    service = CustomerService(db)
    result = service.list_cached(query=q, limit=limit, offset=offset)
    if user:
        audit_action(db, user, action="customers.list", details={"query": q, "total": result.total})
    return result


@router.get("/search", response_model=CustomerSearchResponse)
def search_customers(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: ProductsReadUser = None,
) -> CustomerSearchResponse:
    service = CustomerService(db)
    token = user.easyone_access_token if user else None
    result = service.search(q, limit=limit, offset=offset, easyone_access_token=token)
    if user:
        audit_action(
            db, user, action="customers.search", details={"query": q}
        )
    return result


@router.get("/{customer_code}", response_model=CustomerResponse)
def get_customer(
    customer_code: str,
    db: DbSession,
    user: ProductsReadUser = None,
) -> CustomerResponse:
    service = CustomerService(db)
    token = user.easyone_access_token if user else None
    customer = service.get_by_code(customer_code, easyone_access_token=token)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente non trovato")
    if user:
        audit_action(
            db, user, action="customers.read", entity_id=customer_code
        )
    return customer
