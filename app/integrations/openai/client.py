"""Deprecato: l'app usa Google Gemini. Mantenuto per compatibilità import."""

from app.integrations.gemini.client import get_gemini_client

__all__ = ["get_gemini_client"]
