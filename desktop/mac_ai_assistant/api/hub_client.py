from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from mac_ai_assistant.credentials import (
    clear_refresh_token,
    load_refresh_token,
    load_saved_login,
    save_refresh_token,
)


class HubClient:
    """Client HTTP verso Integration Hub FastAPI."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._user: dict[str, Any] | None = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    @property
    def user(self) -> dict[str, Any] | None:
        return self._user

    def _headers(self, *, include_auth: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if include_auth and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _store_tokens(self, data: dict[str, Any]) -> None:
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        self._user = data.get("user")
        if self._refresh_token:
            save_refresh_token(self._refresh_token)

    def _clear_tokens(self) -> None:
        self._access_token = None
        self._refresh_token = None
        self._user = None
        clear_refresh_token()

    def _raw_request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        timeout: float | None = None,
        include_auth: bool = True,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=timeout or self.timeout) as client:
            return client.request(
                method,
                url,
                headers=self._headers(include_auth=include_auth),
                json=json,
                params=params,
            )

    def _parse_error_detail(self, response: httpx.Response) -> str:
        detail = response.text
        if response.content:
            try:
                payload = response.json()
                if isinstance(payload, dict) and payload.get("detail"):
                    detail = str(payload["detail"])
            except Exception:
                pass
        return str(detail).strip() if detail else ""

    def _is_auth_error(self, status_code: int, detail: str) -> bool:
        if status_code not in (401, 403):
            return False
        lowered = detail.lower()
        return any(
            token in lowered
            for token in (
                "token",
                "scadut",
                "sessione",
                "autenticazione",
                "revocat",
            )
        )

    def _refresh_access_token(self) -> bool:
        refresh = self._refresh_token or load_refresh_token()
        if not refresh:
            return False
        try:
            response = self._raw_request(
                "POST",
                "/api/auth/refresh",
                json={"refresh_token": refresh},
                include_auth=False,
            )
        except httpx.HTTPError:
            return False
        if response.status_code >= 400:
            return False
        try:
            data = response.json()
        except Exception:
            return False
        if not isinstance(data, dict) or "access_token" not in data:
            return False
        self._store_tokens(data)
        return True

    def _relogin_with_saved_credentials(self) -> bool:
        username, password, remember = load_saved_login()
        if not remember or not username or not password:
            return False
        try:
            self.login(username, password)
            return True
        except Exception:
            return False

    def try_restore_session(self) -> bool:
        """Ripristina la sessione da refresh token salvato."""
        if self.is_authenticated:
            return True
        saved = load_refresh_token()
        if saved:
            self._refresh_token = saved
            if self._refresh_access_token():
                return True
        return self._relogin_with_saved_credentials()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        timeout: float | None = None,
        _auth_retry: bool = True,
    ) -> Any:
        try:
            response = self._raw_request(
                method,
                path,
                json=json,
                params=params,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "Il servizio impiega troppo tempo a rispondere. "
                "Le domande tecniche possono richiedere alcuni minuti "
                "(caricamento modelli e ricerca sui manuali di rete): attendere e riprovare."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "Servizio non raggiungibile. Verificare la connessione di rete."
            ) from exc

        if response.status_code >= 400:
            detail = self._parse_error_detail(response)
            if _auth_retry and self._is_auth_error(response.status_code, detail):
                if self._refresh_access_token():
                    return self._request(
                        method,
                        path,
                        json=json,
                        params=params,
                        timeout=timeout,
                        _auth_retry=False,
                    )
                if self._relogin_with_saved_credentials():
                    return self._request(
                        method,
                        path,
                        json=json,
                        params=params,
                        timeout=timeout,
                        _auth_retry=False,
                    )
                self._clear_tokens()
                raise RuntimeError(
                    "Sessione scaduta. Esci dall'applicazione e accedi di nuovo "
                    "con le credenziali EasyOne."
                )

            if response.status_code in (401, 403):
                message = detail
                if "Credenziali" in message or "non valide" in message.lower():
                    raise RuntimeError("Utente o password EasyOne non corretti.")
                if "EasyOne CRM" in message or "mock" in message.lower():
                    raise RuntimeError(
                        "Il servizio locale usa ancora una configurazione EasyOne errata. "
                        "Chiudere completamente MAC AI Assistant, attendere 5 secondi e riaprire."
                    )
                raise RuntimeError(message or "Accesso non riuscito.")

            if response.status_code == 503:
                raise RuntimeError(
                    detail
                    or "Database locale non disponibile. Avviare PostgreSQL e riprovare."
                )
            if response.status_code in (502, 504):
                raise RuntimeError(
                    detail or "Servizio temporaneamente non disponibile. Riprovare tra poco."
                )
            if response.status_code >= 500:
                raise RuntimeError(
                    detail
                    or "Errore del servizio locale. Verificare PostgreSQL e i log in AppData."
                )
            raise RuntimeError(detail or "Richiesta non riuscita")

        if not response.content:
            return None
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/health")

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/api/auth/login",
            json={"username": username, "password": password},
            _auth_retry=False,
        )
        self._store_tokens(data)
        return data

    def logout(self) -> None:
        if self._access_token:
            try:
                self._request("POST", "/api/auth/logout")
            except Exception:
                pass
        self._clear_tokens()

    def search_products(self, query: str, limit: int = 20) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/products/search",
            params={"q": query, "limit": limit},
        )

    def list_customers(
        self,
        *,
        query: str = "",
        limit: int = 2000,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/customers/list",
            params={"q": query, "limit": limit, "offset": offset},
        )

    def list_all_customers(self, *, query: str = "") -> dict[str, Any]:
        """Carica tutte le pagine dell'archivio locale clienti."""
        page_size = 2000
        offset = 0
        all_items: list[dict[str, Any]] = []
        total = 0

        while True:
            data = self.list_customers(query=query, limit=page_size, offset=offset)
            items = data.get("items", [])
            total = int(data.get("total", len(items)))
            all_items.extend(items)
            if len(all_items) >= total or not items or len(items) < page_size:
                break
            offset += len(items)

        return {"items": all_items, "total": total}

    def search_customers(self, query: str, *, limit: int = 500) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/customers/search",
            params={"q": query, "limit": limit},
        )

    def get_customer(self, customer_code: str) -> dict[str, Any] | None:
        code = quote(customer_code.strip(), safe="")
        try:
            return self._request("GET", f"/api/customers/{code}")
        except RuntimeError as exc:
            if "404" in str(exc) or "non trovato" in str(exc).lower():
                return None
            raise

    def search_warehouse(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/api/warehouse/search", params={"q": query})

    def search_documents(self, query: str) -> dict[str, Any]:
        return self._request("GET", "/api/documents/search", params={"q": query})

    def import_documents_folder(
        self,
        folder_path: str,
        *,
        recursive: bool = True,
        index_pdfs: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/documents/import-folder",
            json={
                "folder_path": folder_path,
                "recursive": recursive,
                "index_pdfs": index_pdfs,
            },
            timeout=300.0,
        )

    def search_documents_web(self, query: str) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/documents/search-web",
            params={"q": query},
            timeout=90.0,
        )

    def ask_assistant(
        self,
        question: str,
        *,
        mode: str = "commercial",
        history: list[dict[str, str]] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"question": question, "mode": mode}
        if history:
            payload["history"] = history
        if timeout is None:
            timeout = 300.0 if mode == "technical" else 90.0
        return self._request("POST", "/api/chat/ask", json=payload, timeout=timeout)

    def list_internal_chat(
        self,
        *,
        channel: str = "generale",
        limit: int = 100,
        since: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"channel": channel, "limit": limit}
        if since:
            params["since"] = since
        return self._request("GET", "/api/internal-chat/messages", params=params)

    def send_internal_chat(
        self,
        body: str,
        *,
        channel: str = "generale",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/internal-chat/messages",
            json={"body": body, "channel": channel},
        )

    def copilot_analyze(self, query: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/commercial-copilot/analyze",
            json={"query": query},
        )

    def sales_analytics(self) -> dict[str, Any]:
        return self._request("GET", "/api/analytics/sales")

    def customer_analytics(self, customer_code: str) -> dict[str, Any]:
        code = quote(customer_code.strip(), safe="")
        return self._request("GET", f"/api/analytics/customer/{code}")

    def customer_maxy_suggestions(self, customer_code: str) -> dict[str, Any]:
        code = quote(customer_code.strip(), safe="")
        return self._request(
            "GET",
            f"/api/analytics/customer/{code}/maxy-suggestions",
            timeout=90.0,
        )

    def whatsapp_draft(
        self,
        message: str,
        *,
        customer_phone: str | None = None,
        customer_code: str | None = None,
        product_context: str | None = None,
        send_via_api: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/whatsapp/draft",
            json={
                "inbound_message": message,
                "customer_phone": customer_phone,
                "customer_code": customer_code,
                "product_context": product_context,
                "send_via_api": send_via_api,
            },
        )

    def sync_orders(self) -> dict[str, Any]:
        return self._request("POST", "/api/sync/orders")

    def check_updates(self, current_version: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/updates/check",
            json={"current_version": current_version},
        )

    def mail_provider_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/mail/status")

    def mail_list_accounts(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/mail/accounts")

    def mail_oauth_start(self, provider: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/mail/oauth/start",
            json={"provider": provider},
        )

    def mail_oauth_status(self, state: str) -> dict[str, Any]:
        return self._request("GET", f"/api/mail/oauth/status/{state}")

    def mail_disconnect_account(self, account_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/api/mail/accounts/{account_id}")

    def mail_list_messages(
        self,
        account_id: str,
        *,
        limit: int = 50,
        folder: str = "inbox",
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/mail/messages",
            params={"account_id": account_id, "limit": limit, "folder": folder},
        )

    def mail_get_message(self, account_id: str, message_id: str) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/mail/messages/{message_id}",
            params={"account_id": account_id},
        )

    def calendar_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/calendar/status")

    def calendar_unified(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        include_outlook: bool = True,
        include_easyone: bool = True,
        outlook_account_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "include_outlook": include_outlook,
            "include_easyone": include_easyone,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if outlook_account_id:
            params["outlook_account_id"] = outlook_account_id
        return self._request("GET", "/api/calendar/unified", params=params)

    def mail_send(
        self,
        account_id: str,
        *,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        attachments: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/mail/send",
            json={
                "account_id": account_id,
                "to": to,
                "subject": subject,
                "body": body,
                "cc": cc or [],
                "attachments": attachments or [],
            },
            timeout=120.0,
        )
