from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.exceptions import AuthenticationError, is_authentication_error
from app.core.permissions import Scope, has_scope
from app.db.session import get_db
from app.services.auth_service import AuthService, AuthenticatedUser

DbSession = Annotated[Session, Depends(get_db)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_optional(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser | None:
    settings = get_settings()
    if not credentials:
        if settings.auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticazione richiesta",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    service = AuthService(db)
    try:
        return service.get_current_user(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        if is_authentication_error(exc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise


def get_current_user(
    user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> AuthenticatedUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)]


def require_scope(scope: str | Scope):
    def _dependency(user: CurrentUser) -> AuthenticatedUser:
        settings = get_settings()
        if not settings.auth_required:
            return user
        if not has_scope(user.permissions, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto: {scope}",
            )
        return user

    return _dependency


def optional_scope(scope: str | Scope):
    """Richiede autenticazione+scope solo se AUTH_REQUIRED=true."""

    def _dependency(user: AuthenticatedUser | None = Depends(get_current_user_optional)):
        settings = get_settings()
        if not settings.auth_required:
            return user
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticazione richiesta",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not has_scope(user.permissions, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto: {scope}",
            )
        return user

    return _dependency


AiChatUser = Annotated[AuthenticatedUser | None, Depends(optional_scope(Scope.AI_CHAT))]
AiCopilotUser = Annotated[AuthenticatedUser | None, Depends(optional_scope(Scope.AI_COPILOT))]
ProductsReadUser = Annotated[
    AuthenticatedUser | None, Depends(optional_scope(Scope.PRODUCTS_READ))
]
AdminSyncUser = Annotated[
    AuthenticatedUser | None, Depends(optional_scope(Scope.ADMIN_SYNC))
]
AdminUser = Annotated[AuthenticatedUser, Depends(require_scope(Scope.ADMIN_SYNC))]
MailUser = Annotated[AuthenticatedUser | None, Depends(optional_scope(Scope.MAIL_ACCESS))]
CalendarUser = Annotated[
    AuthenticatedUser | None, Depends(optional_scope(Scope.CALENDAR_READ))
]


def audit_action(
    db: DbSession,
    user: AuthenticatedUser,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    from app.audit.logger import AuditLogger

    logger = AuditLogger(db)
    logger.log(
        session_id=user.session_id,
        easyone_user_id=user.user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.commit()
