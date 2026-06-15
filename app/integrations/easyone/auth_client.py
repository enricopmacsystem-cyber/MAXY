from __future__ import annotations



from abc import ABC, abstractmethod

from dataclasses import dataclass



import httpx



from app.config.settings import Settings, get_settings

from app.core.exceptions import AuthenticationError

from app.core.logging import get_logger

from app.core.permissions import ALL_SCOPES, map_easyone_permissions

from app.integrations.easyone.macsystem_auth import extract_bearer_token, macsystem_login_payload



logger = get_logger(__name__)





@dataclass(frozen=True)

class EasyOneUserProfile:

    user_id: str

    username: str

    display_name: str

    roles: list[str]

    permissions: list[str]

    easyone_access_token: str | None = None





class EasyOneAuthClient(ABC):

    @abstractmethod

    def authenticate(self, username: str, password: str) -> EasyOneUserProfile:

        raise NotImplementedError





class DevEasyOneAuthClient(EasyOneAuthClient):

    """

    Client di sviluppo: simula login EasyOne con utenti configurati in .env.

    Formato DEV_AUTH_USERS: user:password:display_name|role1,role2

    """



    def __init__(self, settings: Settings | None = None) -> None:

        self.settings = settings or get_settings()

        self._users = self._parse_dev_users(self.settings.dev_auth_users)



    @staticmethod

    def _parse_dev_users(raw: str) -> dict[str, dict]:

        users: dict[str, dict] = {}

        if not raw.strip():

            users["admin"] = {

                "password": "admin",

                "display_name": "Amministratore Dev",

                "roles": ["admin"],

                "permissions": sorted(ALL_SCOPES),

            }

            return users



        for entry in raw.split(";"):

            entry = entry.strip()

            if not entry:

                continue

            parts = entry.split(":")

            if len(parts) < 2:

                continue

            username = parts[0]

            password = parts[1]

            display_name = parts[2] if len(parts) > 2 else username

            roles = ["user"]

            permissions = sorted(ALL_SCOPES)

            if len(parts) > 3 and parts[3]:

                roles = [r.strip() for r in parts[3].split(",") if r.strip()]

            users[username] = {

                "password": password,

                "display_name": display_name,

                "roles": roles,

                "permissions": permissions,

            }

        return users



    def authenticate(self, username: str, password: str) -> EasyOneUserProfile:

        user = self._users.get(username)

        if not user or user["password"] != password:

            logger.warning("Dev auth fallita per utente: %s", username)

            raise AuthenticationError("Credenziali EasyOne non valide")



        logger.info("Dev auth riuscita per utente: %s", username)

        return EasyOneUserProfile(

            user_id=f"dev-{username}",

            username=username,

            display_name=user["display_name"],

            roles=user["roles"],

            permissions=user["permissions"],

            easyone_access_token=None,

        )





class HttpEasyOneAuthClient(EasyOneAuthClient):

    """Client HTTP verso API EasyOne CRM (MAC SYSTEM: authentication/Login)."""



    def __init__(self, settings: Settings | None = None) -> None:

        self.settings = settings or get_settings()

        if not self.settings.easyone_base_url:

            raise ValueError("EASYONE_BASE_URL richiesto per HttpEasyOneAuthClient")



    def authenticate(self, username: str, password: str) -> EasyOneUserProfile:

        from app.integrations.easyone.endpoints import EasyOneEndpoints



        endpoints = EasyOneEndpoints.from_settings(self.settings)

        login_path = endpoints.auth_login.strip() or "/authentication/Login"

        url = f"{self.settings.easyone_base_url.rstrip('/')}{login_path}"

        timeout = self.settings.easyone_timeout_seconds

        headers = {

            "Accept": "application/json",

            "Content-Type": "application/json",

            "Content-Language": "it",

        }



        try:

            payload = macsystem_login_payload(username, password, self.settings)

        except AuthenticationError:

            raise



        try:

            with httpx.Client(timeout=timeout) as client:

                response = client.post(url, headers=headers, json=payload)

        except httpx.HTTPError as exc:

            logger.error("Errore HTTP login EasyOne: %s", exc)

            raise AuthenticationError("Servizio EasyOne CRM non raggiungibile") from exc



        if response.status_code == 401:
            raise AuthenticationError("Credenziali EasyOne non valide")

        if response.status_code == 404:
            logger.error("Login EasyOne: endpoint non trovato su %s", url)
            raise AuthenticationError(
                "EasyOne CRM non configurato correttamente (URL errato). "
                "Contattare l'amministratore."
            )

        if response.status_code >= 400:
            logger.error(
                "Login EasyOne fallito: status=%s body=%s",
                response.status_code,
                response.text[:300],
            )
            raise AuthenticationError("Errore autenticazione EasyOne CRM")



        token = extract_bearer_token(response)

        permissions = sorted(ALL_SCOPES)

        logger.info("Login EasyOne CRM riuscito per utente: %s", username)



        return EasyOneUserProfile(

            user_id=username,

            username=username,

            display_name=username,

            roles=["user"],

            permissions=permissions,

            easyone_access_token=token,

        )





def get_easyone_auth_client(settings: Settings | None = None) -> EasyOneAuthClient:

    settings = settings or get_settings()

    base_url = (settings.easyone_base_url or "").strip()

    if base_url:

        return HttpEasyOneAuthClient(settings)

    if settings.easyone_auth_mode == "dev":

        return DevEasyOneAuthClient(settings)

    logger.warning(

        "EASYONE_BASE_URL non configurato: impossibile usare credenziali EasyOne CRM reali"

    )

    return DevEasyOneAuthClient(settings)


