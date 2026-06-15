from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import DbSession
from app.core.exceptions import OrderImportError, ProductNotFoundError
from app.core.logging import get_logger
from app.schemas.recommendation import (
    ProductRecommendationResponse,
    RecommendationImportResult,
    RecomputeResult,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/import", response_model=RecommendationImportResult)
async def import_order_history(
    db: DbSession,
    file: UploadFile = File(..., description="File Excel (.xlsx) storico ordini"),
    recompute: bool = Query(default=True, description="Ricalcola raccomandazioni dopo import"),
) -> RecommendationImportResult:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Caricare un file Excel .xlsx")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File Excel vuoto")

    service = RecommendationService(db)
    try:
        from io import BytesIO

        return service.import_orders_from_excel(BytesIO(content), recompute=recompute)
    except OrderImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recompute", response_model=RecomputeResult)
def recompute_recommendations(db: DbSession) -> RecomputeResult:
    """Ricalcola co-occorrenze e correlazioni dallo storico ordini."""
    service = RecommendationService(db)
    result = service.recompute_recommendations()
    logger.info(
        "Ricalcolo via API: %d prodotti, %d coppie",
        result.products_with_stats,
        result.cooccurrence_pairs,
    )
    return result


@router.get("/{internal_code}", response_model=ProductRecommendationResponse)
def get_product_recommendations(
    internal_code: str,
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=50),
) -> ProductRecommendationResponse:
    """
    Restituisce frequenza di acquisto e prodotti acquistati insieme con % correlazione.
    """
    service = RecommendationService(db)
    try:
        return service.get_recommendations_for_product(internal_code, limit=limit)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
