from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from mac_ai_assistant.branding import APP_VERSION_LABEL, BUILD_NAME, release_notes_path, window_title
from mac_ai_assistant.ui.theme_preferences import dialog_style


class ReleaseInfoDialog(QDialog):
    """Mostra il file testuale con funzioni, correzioni e motivazioni."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Release info")
        self.setMinimumSize(640, 520)
        self.resize(720, 560)
        self.setStyleSheet(dialog_style())

        layout = QVBoxLayout(self)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 10))
        self.text.setPlainText(self._load_notes())
        layout.addWidget(self.text)

        row = QHBoxLayout()
        row.addStretch()
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _load_notes(self) -> str:
        path = release_notes_path()
        if path and path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except Exception as exc:
                return f"Impossibile leggere le note di rilascio:\n{exc}"

        return (
            f"{window_title()} — build {BUILD_NAME}\n"
            f"Versione: {APP_VERSION_LABEL}\n\n"
            f"File release_notes_it.txt non trovato.\n"
            f"Percorso cercato: {path or 'n/d'}"
        )
