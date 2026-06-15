from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.audit.middleware import RequestLoggingMiddleware
from app.config.settings import get_settings
from app.core.logging import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings.cache_clear()
    settings = get_settings()
    setup_logging(settings.log_level)
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    api_url = (settings.easyone_base_url or "").strip()
    if api_url:
        logger.info("EasyOne CRM API: %s", api_url)
        if "8090" in api_url or "127.0.0.1" in api_url:
            logger.warning(
                "EasyOne punta a mock locale (%s): verificare .env e riavviare l'Hub",
                api_url,
            )

    if settings.jwt_secret_key == "change-me-in-production-mac-ai-assistant":
        logger.warning(
            "JWT_SECRET_KEY non configurato: impostare un valore randomico in hub.env"
        )

    import threading

    threading.Thread(
        target=_warmup_technical_engine,
        name="technical-engine-warmup",
        daemon=True,
    ).start()

    yield


def _warmup_technical_engine() -> None:
    try:
        from app.integrations.macsystem_bot.adapter import warmup_technical_engine

        warmup_technical_engine()
    except Exception:
        pass


app = FastAPI(
    title="MAC AI Assistant",
    description="Piattaforma integrata EasyOne, magazzino, catalogo, PDF, AI e WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_frontend() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    return FileResponse(index_path)
