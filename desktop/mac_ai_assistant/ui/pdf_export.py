from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from mac_ai_assistant.export.pdf_builder import build_text_pdf


def default_exports_dir() -> Path:
    documents = Path.home() / "Documents" / "MAC AI Assistant"
    documents.mkdir(parents=True, exist_ok=True)
    return documents


def suggest_pdf_path(prefix: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in prefix)[:40]
    stamp = date.today().strftime("%Y%m%d")
    return default_exports_dir() / f"{safe}_{stamp}.pdf"


def export_text_to_pdf(
    parent: QWidget,
    *,
    title: str,
    body: str,
    default_name: str,
    subtitle: str | None = None,
) -> Path | None:
    if not body.strip():
        QMessageBox.information(parent, "Esporta PDF", "Non c'è contenuto da esportare.")
        return None
    path, _ = QFileDialog.getSaveFileName(
        parent,
        "Salva PDF",
        str(suggest_pdf_path(default_name)),
        "PDF (*.pdf)",
    )
    if not path:
        return None
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    try:
        saved = build_text_pdf(
            title=title,
            body=body,
            output_path=Path(path),
            subtitle=subtitle,
        )
    except Exception as exc:
        QMessageBox.warning(parent, "Esporta PDF", f"Impossibile creare il PDF:\n{exc}")
        return None
    notify_export_done(parent, saved)
    return saved


def notify_export_done(parent: QWidget, path: Path) -> None:
    answer = QMessageBox.question(
        parent,
        "PDF creato",
        f"File salvato in:\n{path}\n\nAprire il PDF adesso?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if answer == QMessageBox.StandardButton.Yes:
        _open_file(path)


def _open_file(path: Path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass
