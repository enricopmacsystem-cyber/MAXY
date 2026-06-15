from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import AdminUser, DbSession, audit_action
from app.core.exceptions import (
    CompatibilityError,
    ProductImportError,
    ProductNotFoundError,
)
from app.core.logging import get_logger
from app.schemas.compatibility import (
    CompatibilityLinkCreate,
    CompatibilityLinkResponse,
    ProductDetailResponse,
    ProductSearchResultWithCompatibility,
    ProductSearchWithCompatibilityResponse,
)
from app.schemas.product import (
    ProductCreate,
    ProductImportResult,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.compatibility_service import CompatibilityService
from app.services.product_service import ProductService

router = APIRouter()
logger = get_logger(__name__)


def _to_product_response(product) -> ProductResponse:
    return ProductResponse.model_validate(product)


@router.get("", response_model=ProductListResponse)
def list_products(
    db: DbSession,
    category: str | None = Query(default=None),
    manufacturer: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductListResponse:
    service = ProductService(db)
    products, total = service.list_products(
        category=category,
        manufacturer=manufacturer,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[_to_product_response(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=ProductSearchWithCompatibilityResponse)
def search_products(
    db: DbSession,
    q: str = Query(..., min_length=1, max_length=500, description="Testo da cercare"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductSearchWithCompatibilityResponse:
    product_service = ProductService(db)
    compatibility_service = CompatibilityService(db)

    hits, total = product_service.search_products(q, limit=limit, offset=offset)
    products = [hit.product for hit in hits]
    bundles = compatibility_service.get_bundles_for_products(products)

    return ProductSearchWithCompatibilityResponse(
        items=[
            ProductSearchResultWithCompatibility(
                product=_to_product_response(hit.product),
                rank=hit.rank,
                compatibility=bundles[hit.product.id],
            )
            for hit in hits
        ],
        total=total,
        limit=limit,
        offset=offset,
        query=q,
    )


@router.get("/{internal_code}", response_model=ProductDetailResponse)
def get_product(internal_code: str, db: DbSession) -> ProductDetailResponse:
    product_service = ProductService(db)
    compatibility_service = CompatibilityService(db)

    try:
        product = product_service.get_by_internal_code(internal_code)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ProductDetailResponse(
        product=_to_product_response(product),
        compatibility=compatibility_service.get_bundle_for_product(product),
    )


@router.post(
    "/{internal_code}/compatibility",
    response_model=CompatibilityLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_compatibility_link(
    internal_code: str,
    payload: CompatibilityLinkCreate,
    db: DbSession,
    user: AdminUser,
) -> CompatibilityLinkResponse:
    service = CompatibilityService(db)
    try:
        link = service.add_compatibility_link(
            product_code=internal_code,
            related_code=payload.related_internal_code,
            compatibility_type=payload.compatibility_type,
            notes=payload.notes,
            sort_order=payload.sort_order,
        )
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompatibilityError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit_action(
        db,
        user,
        action="products.compatibility.add",
        entity_id=internal_code,
        details={"related": payload.related_internal_code},
    )
    return link


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, user: AdminUser) -> ProductResponse:
    service = ProductService(db)
    data = payload.model_dump(mode="python")
    data["manual_url"] = str(data["manual_url"]) if data.get("manual_url") else None
    data["datasheet_url"] = (
        str(data["datasheet_url"]) if data.get("datasheet_url") else None
    )
    try:
        product = service.create_product(data)
    except ProductImportError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit_action(db, user, action="products.create", entity_id=product.internal_code)
    return _to_product_response(product)


@router.put("/{internal_code}", response_model=ProductResponse)
def update_product(
    internal_code: str,
    payload: ProductUpdate,
    db: DbSession,
    user: AdminUser,
) -> ProductResponse:
    service = ProductService(db)
    data = payload.model_dump(exclude_unset=True, mode="python")
    if "manual_url" in data and data["manual_url"] is not None:
        data["manual_url"] = str(data["manual_url"])
    if "datasheet_url" in data and data["datasheet_url"] is not None:
        data["datasheet_url"] = str(data["datasheet_url"])
    try:
        product = service.update_product(internal_code, data)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_action(db, user, action="products.update", entity_id=internal_code)
    return _to_product_response(product)


@router.post("/import", response_model=ProductImportResult)
async def import_products(
    db: DbSession,
    user: AdminUser,
    file: UploadFile = File(..., description="File Excel (.xlsx)"),
) -> ProductImportResult:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Caricare un file Excel con estensione .xlsx",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File Excel vuoto")

    service = ProductService(db)
    try:
        from io import BytesIO

        result = service.import_from_excel(BytesIO(content))
    except ProductImportError as exc:
        logger.error("Import Excel fallito: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "Import via API completato: importati=%d, aggiornati=%d",
        result.imported,
        result.updated,
    )
    audit_action(
        db,
        user,
        action="products.import",
        details={"imported": result.imported, "updated": result.updated},
    )
    return result
