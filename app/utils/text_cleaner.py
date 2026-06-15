import re


def clean_text(text: str) -> str:
    """Normalizza spazi e caratteri di controllo dal testo estratto."""
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()
