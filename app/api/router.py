from fastapi import APIRouter

from app.api.routes import (
    analytics,
    auth,
    calendar,
    chat,
    commercial_copilot,
    customers,
    documents,
    health,
    internal_chat,
    mail,
    products,
    recommendations,
    sync,
    updates,
    warehouse,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(warehouse.router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(
    internal_chat.router,
    prefix="/internal-chat",
    tags=["internal-chat"],
)
api_router.include_router(mail.router, prefix="/mail", tags=["mail"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(updates.router, prefix="/updates", tags=["updates"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["recommendations"],
)
api_router.include_router(
    commercial_copilot.router,
    prefix="/commercial-copilot",
    tags=["commercial-copilot"],
)
