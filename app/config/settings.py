import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_EASYONE_DOTENV_KEYS = (
    "EASYONE_API_URL",
    "EASYONE_BASE_URL",
    "EASYONE_EVENTS_URL",
    "EASYONE_EVENTS_BASE_URL",
    "EASYONE_TENANT_ID",
    "EASYONE_PORTAL_URL",
    "EASYONE_CRM_URL",
    "EASYONE_AUTH_MODE",
    "EASYONE_MODE",
)


def _hub_env_candidates() -> list[Path]:
    paths: list[Path] = []
    hub_env = os.getenv("MAC_AI_HUB_ENV", "").strip()
    if hub_env:
        paths.append(Path(hub_env))
    appdata = os.getenv("APPDATA", "").strip()
    if appdata:
        paths.append(Path(appdata) / "MAC AI Assistant" / "hub.env")
    paths.append(PROJECT_ROOT / ".env")
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _read_dotenv_easyone_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in _hub_env_candidates():
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in _EASYONE_DOTENV_KEYS and val:
                values[key] = val
    return values


def _is_mock_easyone_url(url: str) -> bool:
    lowered = url.lower()
    return "8090" in lowered or "127.0.0.1" in lowered or "localhost" in lowered


def _prefer_dotenv_easyone_over_mock_process_env() -> None:
    """
    EASYONE_BASE_URL di sviluppo (es. :8090) ha priorità su hub.env in pydantic.
    Forziamo i valori Mac System da hub.env / .env quando presenti.
    """
    file_vals = _read_dotenv_easyone_values()
    api_url = file_vals.get("EASYONE_API_URL") or file_vals.get("EASYONE_BASE_URL", "")
    if not api_url or "macsystem" not in api_url.lower():
        return

    proc_base = os.environ.get("EASYONE_BASE_URL", "")
    proc_api = os.environ.get("EASYONE_API_URL", "")
    if (
        _is_mock_easyone_url(proc_base)
        or _is_mock_easyone_url(proc_api)
        or proc_base != api_url
        or (proc_api and proc_api != api_url)
    ):
        for key in _EASYONE_DOTENV_KEYS:
            os.environ.pop(key, None)
        for key, val in file_vals.items():
            os.environ[key] = val
        os.environ["EASYONE_API_URL"] = api_url
        os.environ["EASYONE_BASE_URL"] = file_vals.get("EASYONE_BASE_URL") or api_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = Field("", alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field("gemini-2.5-flash-lite", alias="GEMINI_CHAT_MODEL")
    gemini_embedding_model: str = Field(
        "text-embedding-004",
        alias="GEMINI_EMBEDDING_MODEL",
    )
    gemini_chat_temperature: float = Field(0.1, alias="GEMINI_CHAT_TEMPERATURE")

    qdrant_host: str = Field("localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(6333, alias="QDRANT_PORT")
    qdrant_collection: str = Field("document_chunks", alias="QDRANT_COLLECTION")

    documents_dir: Path = Field(
        default_factory=lambda: PROJECT_ROOT / "documents",
        alias="DOCUMENTS_DIR",
    )
    chunk_size: int = Field(800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(100, alias="CHUNK_OVERLAP")
    embedding_batch_size: int = Field(50, alias="EMBEDDING_BATCH_SIZE")

    rag_top_k: int = Field(5, alias="RAG_TOP_K")
    rag_score_threshold: float = Field(0.35, alias="RAG_SCORE_THRESHOLD")

    database_url: str = Field(
        "postgresql+psycopg2://postgres:postgres@localhost:5432/tech_assistant",
        alias="DATABASE_URL",
    )

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Autenticazione EasyOne
    auth_required: bool = Field(False, alias="AUTH_REQUIRED")
    jwt_secret_key: str = Field(
        "change-me-in-production-mac-ai-assistant",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # EasyOne integration
    easyone_mode: str = Field("local", alias="EASYONE_MODE")  # local | http | hybrid
    easyone_auth_mode: str = Field("http", alias="EASYONE_AUTH_MODE")  # dev | http
    easyone_base_url: str = Field(
        "",
        validation_alias=AliasChoices("EASYONE_BASE_URL", "EASYONE_API_URL"),
    )
    easyone_portal_url: str = Field(
        "",
        validation_alias=AliasChoices("EASYONE_PORTAL_URL", "EASYONE_CRM_URL"),
    )
    easyone_events_base_url: str = Field(
        "",
        validation_alias=AliasChoices("EASYONE_EVENTS_BASE_URL", "EASYONE_EVENTS_URL"),
    )
    easyone_tenant_id: str = Field("", alias="EASYONE_TENANT_ID")
    easyone_neutral_customer_id: str = Field("", alias="EASYONE_NEUTRAL_CUSTOMER_ID")
    easyone_api_key: str = Field("", alias="EASYONE_API_KEY")
    easyone_timeout_seconds: float = Field(15.0, alias="EASYONE_TIMEOUT_SECONDS")
    dev_auth_users: str = Field("", alias="DEV_AUTH_USERS")

    # ERP (magazzino/listini) — URL separato se diverso da EasyOne CRM
    erp_base_url: str = Field("", alias="ERP_BASE_URL")
    erp_api_key: str = Field("", alias="ERP_API_KEY")

    # Path API EasyOne configurabili (allineare con documentazione vendor)
    easyone_path_auth_login: str = Field(
        "/authentication/Login", alias="EASYONE_PATH_AUTH_LOGIN"
    )
    easyone_path_auth_refresh: str = Field("/api/auth/refresh", alias="EASYONE_PATH_AUTH_REFRESH")
    easyone_path_products_search: str = Field("/articles", alias="EASYONE_PATH_PRODUCTS_SEARCH")
    easyone_path_product_by_code: str = Field("/articles/{code}", alias="EASYONE_PATH_PRODUCT_BY_CODE")
    easyone_path_stock_by_code: str = Field("/inventory/{code}", alias="EASYONE_PATH_STOCK_BY_CODE")
    easyone_path_stock_search: str = Field("/inventory", alias="EASYONE_PATH_STOCK_SEARCH")
    easyone_path_customers_search: str = Field("/people", alias="EASYONE_PATH_CUSTOMERS_SEARCH")
    easyone_path_customer_by_code: str = Field("/people/{code}", alias="EASYONE_PATH_CUSTOMER_BY_CODE")
    easyone_path_orders_search: str = Field("/joborders", alias="EASYONE_PATH_ORDERS_SEARCH")
    easyone_path_order_by_number: str = Field("/joborders/{order_number}", alias="EASYONE_PATH_ORDER_BY_NUMBER")
    easyone_path_tickets_by_event: str = Field("/tickets/{event_id}", alias="EASYONE_PATH_TICKETS_BY_EVENT")
    easyone_path_events_create: str = Field("/Event", alias="EASYONE_PATH_EVENTS_CREATE")
    easyone_path_events_basic_info: str = Field(
        "/event/GetEventBasicInfo/{app_id}", alias="EASYONE_PATH_EVENTS_BASIC_INFO"
    )
    easyone_path_calendar_events: str = Field(
        "/calendar/events", alias="EASYONE_PATH_CALENDAR_EVENTS"
    )
    easyone_path_documents_by_product: str = Field(
        "/api/documents/product/{code}", alias="EASYONE_PATH_DOCUMENTS_BY_PRODUCT"
    )

    # Assistente AI (branding risposte)
    ai_assistant_name: str = Field("Maxy", alias="AI_ASSISTANT_NAME")

    # Assistente tecnico (bot manuali Mac System — ChromaDB + Claude)
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    chroma_dir: str = Field(r"C:\macsystem\chroma_db", alias="CHROMA_DIR")
    documents_network_manual_path: str = Field(
        "",
        alias="DOCUMENTS_NETWORK_MANUAL_PATH",
    )
    documents_network_datasheet_path: str = Field(
        "",
        alias="DOCUMENTS_NETWORK_DATASHEET_PATH",
    )
    macsystem_local_manual_path: str = Field(
        r"C:\macsystem\manuali",
        alias="MACSYSTEM_LOCAL_MANUAL_PATH",
    )
    technical_chat_model: str = Field(
        "claude-opus-4-5",
        alias="TECHNICAL_CHAT_MODEL",
    )

    # Desktop / updates
    app_current_version: str = Field("1.0.0", alias="APP_CURRENT_VERSION")
    hub_base_url: str = Field("http://127.0.0.1:8000", alias="HUB_BASE_URL")

    # WhatsApp Business (fase 2 — invio diretto)
    whatsapp_api_url: str = Field("", alias="WHATSAPP_API_URL")
    whatsapp_api_token: str = Field("", alias="WHATSAPP_API_TOKEN")

    # Posta — OAuth Gmail / Microsoft Outlook
    gmail_client_id: str = Field("", alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field("", alias="GMAIL_CLIENT_SECRET")
    microsoft_client_id: str = Field("", alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str = Field("", alias="MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id: str = Field("common", alias="MICROSOFT_TENANT_ID")
    mail_oauth_redirect_uri: str = Field(
        "http://127.0.0.1:8000/api/mail/oauth/callback",
        alias="MAIL_OAUTH_REDIRECT_URI",
    )

    @property
    def gmail_oauth_configured(self) -> bool:
        return bool((self.gmail_client_id or "").strip() and (self.gmail_client_secret or "").strip())

    @property
    def microsoft_oauth_configured(self) -> bool:
        return bool(
            (self.microsoft_client_id or "").strip()
            and (self.microsoft_client_secret or "").strip()
        )

    @property
    def ai_configured(self) -> bool:
        return bool((self.gemini_api_key or "").strip())

    @property
    def technical_ai_configured(self) -> bool:
        return bool((self.anthropic_api_key or "").strip())

    @property
    def openai_configured(self) -> bool:
        """Deprecato — usare ai_configured (Gemini)."""
        return self.ai_configured

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def embedding_dimensions(self) -> int:
        return 768


def _load_hub_env_files() -> None:
    """Carica hub.env (installazione desktop) prima di costruire Settings."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    seen: set[Path] = set()
    for path in _hub_env_candidates():
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        load_dotenv(path, override=False)


@lru_cache
def get_settings() -> Settings:
    _load_hub_env_files()
    _prefer_dotenv_easyone_over_mock_process_env()
    return Settings()


settings = get_settings()
