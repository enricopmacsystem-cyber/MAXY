from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import DbSession, bearer_scheme
from app.core.exceptions import AuthenticationError, is_authentication_error
from app.core.logging import get_logger
from app.schemas.auth import LoginRequest, RefreshRequest, SessionInfo, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()
logger = get_logger(__name__)


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _raise_auth_http_error(exc: Exception) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=str(exc),
    ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    """Login con credenziali EasyOne — nessun utente locale."""
    service = AuthService(db)
    try:
        return service.login(
            payload.username,
            payload.password,
            ip_address=_client_ip(request),
        )
    except AuthenticationError as exc:
        _raise_auth_http_error(exc)
    except SQLAlchemyError as exc:
        logger.exception("Login fallito: database non disponibile")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database Hub non disponibile. Avviare PostgreSQL "
                "(es. docker compose up -d) e riprovare."
            ),
        ) from exc
    except Exception as exc:
        if is_authentication_error(exc):
            _raise_auth_http_error(exc)
        logger.exception("Login fallito: errore imprevisto")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno durante l'accesso. Consultare i log Hub in AppData.",
        ) from exc


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshRequest,
    request: Request,
    db: DbSession,
) -> TokenResponse:
    service = AuthService(db)
    try:
        return service.refresh(payload.refresh_token, ip_address=_client_ip(request))
    except AuthenticationError as exc:
        _raise_auth_http_error(exc)
    except Exception as exc:
        if is_authentication_error(exc):
            _raise_auth_http_error(exc)
        raise


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    service = AuthService(db)
    token = credentials.credentials if credentials else ""
    if token:
        service.logout(token, ip_address=_client_ip(request))


@router.get("/me", response_model=SessionInfo)
def current_session(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SessionInfo:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token mancante")
    service = AuthService(db)
    try:
        return service.get_session_info(credentials.credentials)
    except AuthenticationError as exc:
        _raise_auth_http_error(exc)
    except Exception as exc:
        if is_authentication_error(exc):
            _raise_auth_http_error(exc)
        raise
