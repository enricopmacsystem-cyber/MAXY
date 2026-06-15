from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.core.permissions import map_easyone_permissions
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
)
from app.integrations.easyone.auth_client import get_easyone_auth_client
from app.repositories.audit_repo import AuditRepository
from app.repositories.session_repo import SessionRepository
from app.schemas.auth import SessionInfo, TokenResponse, UserProfile

logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    session_id: uuid.UUID
    user_id: str
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    easyone_access_token: str | None = None


class AuthService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.session_repo = SessionRepository(session)
        self.audit_repo = AuditRepository(session)
        self.auth_client = get_easyone_auth_client(self.settings)

    def login(
        self,
        username: str,
        password: str,
        *,
        ip_address: str | None = None,
    ) -> TokenResponse:
        profile = self.auth_client.authenticate(username, password)
        permissions = map_easyone_permissions(profile.permissions)
        if not permissions:
            permissions = profile.permissions

        refresh_token = generate_refresh_token()
        session_id = uuid.uuid4()
        session_expires = datetime.now(UTC) + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )

        access_token = create_access_token(
            session_id=session_id,
            easyone_user_id=profile.user_id,
            username=profile.username,
            roles=profile.roles,
            permissions=permissions,
        )

        user_session = self.session_repo.create(
            session_id=session_id,
            easyone_user_id=profile.user_id,
            easyone_username=profile.username,
            display_name=profile.display_name,
            roles=profile.roles,
            permissions=permissions,
            token_hash=hash_token(access_token),
            refresh_token_hash=hash_token(refresh_token),
            expires_at=session_expires,
            easyone_access_token=profile.easyone_access_token,
        )

        self.audit_repo.log(
            session_id=user_session.id,
            easyone_user_id=profile.user_id,
            action="auth.login",
            details={"username": profile.username},
            ip_address=ip_address,
        )
        self.session.commit()

        logger.info("Login riuscito: %s (%s)", profile.username, profile.user_id)
        return self._build_token_response(
            access_token=access_token,
            refresh_token=refresh_token,
            profile=profile,
            permissions=permissions,
        )

    def refresh(self, refresh_token: str, *, ip_address: str | None = None) -> TokenResponse:
        refresh_hash = hash_token(refresh_token)
        user_session = self.session_repo.get_by_refresh_hash(refresh_hash)
        if not user_session:
            raise AuthenticationError("Refresh token non valido")
        if user_session.expires_at < datetime.now(UTC):
            self.session_repo.delete_session(user_session.id)
            self.session.commit()
            raise AuthenticationError("Sessione scaduta")

        new_refresh = generate_refresh_token()
        permissions = list(user_session.permissions_json or [])
        access_token = create_access_token(
            session_id=user_session.id,
            easyone_user_id=user_session.easyone_user_id,
            username=user_session.easyone_username,
            roles=list(user_session.roles_json or []),
            permissions=permissions,
        )
        session_expires = datetime.now(UTC) + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        self.session_repo.rotate_tokens(
            user_session.id,
            token_hash=hash_token(access_token),
            refresh_token_hash=hash_token(new_refresh),
            expires_at=session_expires,
        )
        self.audit_repo.log(
            session_id=user_session.id,
            easyone_user_id=user_session.easyone_user_id,
            action="auth.refresh",
            ip_address=ip_address,
        )
        self.session.commit()

        profile = UserProfile(
            user_id=user_session.easyone_user_id,
            username=user_session.easyone_username,
            display_name=user_session.display_name or user_session.easyone_username,
            roles=list(user_session.roles_json or []),
            permissions=permissions,
        )
        return self._build_token_response(
            access_token=access_token,
            refresh_token=new_refresh,
            profile=profile,
            permissions=permissions,
        )

    def logout(self, access_token: str, *, ip_address: str | None = None) -> None:
        token_hash = hash_token(access_token)
        user_session = self.session_repo.get_by_token_hash(token_hash)
        if user_session:
            self.audit_repo.log(
                session_id=user_session.id,
                easyone_user_id=user_session.easyone_user_id,
                action="auth.logout",
                ip_address=ip_address,
            )
            self.session_repo.delete_session(user_session.id)
            self.session.commit()

    def get_current_user(self, access_token: str) -> AuthenticatedUser:
        try:
            from app.core.security import decode_access_token

            payload = decode_access_token(access_token)
        except Exception as exc:
            raise AuthenticationError("Token non valido o scaduto") from exc

        session_id = uuid.UUID(str(payload["sid"]))
        user_session = self.session_repo.get_by_id(session_id)
        if not user_session:
            raise AuthenticationError("Sessione non trovata")
        if user_session.expires_at < datetime.now(UTC):
            raise AuthenticationError("Sessione scaduta")
        if user_session.token_hash != hash_token(access_token):
            raise AuthenticationError("Token revocato")

        self.session_repo.touch_activity(session_id)
        self.session.commit()

        return AuthenticatedUser(
            session_id=session_id,
            user_id=str(payload["sub"]),
            username=str(payload.get("username", "")),
            display_name=user_session.display_name or str(payload.get("username", "")),
            roles=list(payload.get("roles", [])),
            permissions=list(payload.get("permissions", [])),
            easyone_access_token=user_session.easyone_access_token,
        )

    def get_session_info(self, access_token: str) -> SessionInfo:
        user = self.get_current_user(access_token)
        user_session = self.session_repo.get_by_id(user.session_id)
        if not user_session:
            raise AuthenticationError("Sessione non trovata")

        return SessionInfo(
            session_id=user.session_id,
            user=UserProfile(
                user_id=user.user_id,
                username=user.username,
                display_name=user.display_name,
                roles=user.roles,
                permissions=user.permissions,
            ),
            expires_at=user_session.expires_at,
            last_activity=user_session.last_activity,
        )

    def _build_token_response(
        self,
        *,
        access_token: str,
        refresh_token: str,
        profile,
        permissions: list[str],
    ) -> TokenResponse:
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
            user=UserProfile(
                user_id=profile.user_id,
                username=profile.username,
                display_name=profile.display_name,
                roles=profile.roles,
                permissions=permissions,
            ),
        )
