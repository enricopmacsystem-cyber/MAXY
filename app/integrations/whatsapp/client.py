from __future__ import annotations

import httpx

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WhatsAppBusinessClient:
    """Client WhatsApp Business Cloud API (Meta)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.whatsapp_api_url and self.settings.whatsapp_api_token)

    def send_text_message(self, to_phone: str, text: str) -> dict:
        if not self.is_configured:
            raise ValueError("WhatsApp API non configurata (WHATSAPP_API_URL / WHATSAPP_API_TOKEN)")

        url = self.settings.whatsapp_api_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {self.settings.whatsapp_api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone.replace("+", "").replace(" ", ""),
            "type": "text",
            "text": {"body": text},
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            logger.error("WhatsApp send failed: %s %s", response.status_code, response.text[:300])
            response.raise_for_status()

        return response.json()
