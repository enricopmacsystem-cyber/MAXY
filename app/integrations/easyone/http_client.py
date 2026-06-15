from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger
from app.integrations.easyone.request_context import merge_query_params

logger = get_logger(__name__)


class EasyOneHttpClient:
    """Client HTTP per API EasyOne e/o ERP collegato."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        access_token: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.access_token = access_token
        self.base_url = (base_url or self.settings.easyone_base_url or "").rstrip("/")
        self.api_key = api_key or self.settings.easyone_api_key

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Content-Language": "it",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _url(self, path: str) -> str:
        if not self.base_url:
            raise ValueError("Base URL API non configurato")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = self._url(path)
        timeout = self.settings.easyone_timeout_seconds
        query = merge_query_params(params, self.settings)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=query or None,
                    json=json,
                )
        except httpx.HTTPError as exc:
            logger.error("HTTP %s %s fallito: %s", method, path, exc)
            raise

        if response.status_code == 404:
            return {}
        if response.status_code >= 400:
            logger.warning(
                "HTTP %s %s → %s: %s",
                method,
                path,
                response.status_code,
                response.text[:300],
            )
            response.raise_for_status()
        if not response.content:
            return {}
        return response.json()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        return self.request("POST", path, json=json, params=params)


def get_erp_client(
    settings: Settings | None = None,
    *,
    access_token: str | None = None,
) -> EasyOneHttpClient:
    """Client verso ERP (magazzino/listini) — URL separato se configurato."""
    settings = settings or get_settings()
    base = settings.erp_base_url or settings.easyone_base_url
    return EasyOneHttpClient(
        settings,
        access_token=access_token,
        base_url=base,
        api_key=settings.erp_api_key or settings.easyone_api_key,
    )
