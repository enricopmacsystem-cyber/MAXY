from __future__ import annotations

from pathlib import Path

from app.config.settings import Settings


def allowed_document_roots(settings: Settings) -> list[Path]:
    roots: list[Path] = []
    for value in (
        settings.documents_dir,
        settings.documents_network_manual_path,
        settings.documents_network_datasheet_path,
        settings.macsystem_local_manual_path,
    ):
        text = str(value or "").strip().strip('"')
        if text:
            roots.append(Path(text))
    return roots


def _normalize_path(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def is_path_under_root(candidate: Path, root: Path) -> bool:
    try:
        _normalize_path(candidate).relative_to(_normalize_path(root))
        return True
    except (ValueError, OSError):
        return False


def is_allowed_document_path(path: Path, settings: Settings) -> bool:
    candidate = _normalize_path(path)
    for root in allowed_document_roots(settings):
        if is_path_under_root(candidate, root):
            return True
    return False


def resolve_allowed_folder(folder_path: str, settings: Settings) -> Path:
    root = Path(folder_path.strip().strip('"'))
    if not root.exists():
        raise FileNotFoundError(f"Percorso non trovato: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Non è una cartella: {root}")
    if not is_allowed_document_path(root, settings):
        allowed = ", ".join(str(r) for r in allowed_document_roots(settings))
        raise PermissionError(
            f"Percorso non consentito: {root}. "
            f"Cartelle ammesse: {allowed or '(nessuna configurata in hub.env)'}"
        )
    return _normalize_path(root)
