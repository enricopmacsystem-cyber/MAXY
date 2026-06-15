from __future__ import annotations

from google import genai

from app.config.settings import Settings, get_settings


def get_gemini_client(settings: Settings | None = None) -> genai.Client:
    config = settings or get_settings()
    api_key = (config.gemini_api_key or "").strip()
    if not api_key:
        raise RuntimeError(
            "Funzione AI non disponibile: GEMINI_API_KEY non configurata. "
            "Aggiungerla in %APPDATA%\\MAC AI Assistant\\hub.env "
            "(chiave gratuita da https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=api_key)
