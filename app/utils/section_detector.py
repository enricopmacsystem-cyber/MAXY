import re

_HEADING_PATTERNS = [
    re.compile(r"^\d+(\.\d+)*[\.\)]?\s+[A-ZÀ-ÿ].{2,120}$"),
    re.compile(r"^(?:CAPITOLO|CHAPTER|SEZIONE|SECTION|PARTE|PART)\s+\d+", re.IGNORECASE),
    re.compile(r"^[A-ZÀ-ÿ0-9][A-ZÀ-ÿ0-9\s\-\/]{3,80}$"),
]


def is_section_heading(line: str) -> bool:
    """Rileva se una riga del PDF sembra un titolo di sezione."""
    candidate = line.strip()
    if not candidate or len(candidate) > 120:
        return False

    if candidate.endswith(".") and not re.match(r"^\d+(\.\d+)*", candidate):
        return False

    for pattern in _HEADING_PATTERNS:
        if pattern.match(candidate):
            return True

    return False


def detect_section_from_text(text: str, fallback: str = "Generale") -> str:
    """
    Restituisce la sezione più probabile all'inizio di un blocco di testo.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if is_section_heading(stripped):
            return stripped
        break

    return fallback


def assign_sections_to_lines(text: str, default_section: str = "Generale") -> list[tuple[str, str]]:
    """
    Associa ogni riga non vuota alla sezione corrente del documento.

    Returns:
        Lista di tuple (section_title, line_content).
    """
    current_section = default_section
    annotated: list[tuple[str, str]] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if is_section_heading(stripped):
            current_section = stripped
            annotated.append((current_section, stripped))
            continue

        annotated.append((current_section, stripped))

    return annotated
