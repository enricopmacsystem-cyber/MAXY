from fastapi import APIRouter, HTTPException, Query



from app.api.dependencies import AiChatUser, DbSession, ProductsReadUser, audit_action

from app.schemas.analytics import (

    CustomerAnalyticsResponse,

    CustomerMaxySuggestionsResponse,

    SalesAnalyticsResponse,

)

from app.services.analytics_service import AnalyticsService



router = APIRouter()





@router.get("/sales", response_model=SalesAnalyticsResponse)

def sales_overview(

    db: DbSession,

    top_n: int = Query(default=10, ge=1, le=50),

    user: ProductsReadUser = None,

) -> SalesAnalyticsResponse:

    service = AnalyticsService(db)

    result = service.get_sales_overview(top_n=top_n)

    if user:

        audit_action(db, user, action="analytics.sales")

    return result





@router.get("/customer/{customer_code}", response_model=CustomerAnalyticsResponse)

def customer_analytics(

    customer_code: str,

    db: DbSession,

    user: ProductsReadUser = None,

) -> CustomerAnalyticsResponse:

    service = AnalyticsService(db)

    token = user.easyone_access_token if user else None

    try:

        result = service.get_customer_analytics(

            customer_code,

            easyone_access_token=token,

        )

    except ValueError as exc:

        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if user:

        audit_action(

            db,

            user,

            action="analytics.customer",

            entity_id=customer_code,

        )

    return result





@router.get(

    "/customer/{customer_code}/maxy-suggestions",

    response_model=CustomerMaxySuggestionsResponse,

)

def customer_maxy_suggestions(

    customer_code: str,

    db: DbSession,

    user: AiChatUser = None,

) -> CustomerMaxySuggestionsResponse:

    service = AnalyticsService(db)

    token = user.easyone_access_token if user else None

    try:

        return service.get_maxy_suggestions_for_customer(

            customer_code,

            easyone_access_token=token,

        )

    except ValueError as exc:

        raise HTTPException(status_code=400, detail=str(exc)) from exc


