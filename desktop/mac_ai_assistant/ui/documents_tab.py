from __future__ import annotations

import os
import webbrowser
from typing import Any

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.api.hub_client import HubClient


class DocumentsTab(QWidget):
    """Documenti: archivio locale, cartelle di rete e ricerca web con Maxy."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._web_results: list[dict[str, Any]] = []
        self._mode = "local"

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Cerca nei documenti indicizzati, importa PDF da cartella locale o di rete "
            "(es. \\\\server\\share\\manuali), oppure chiedi a Maxy di trovare schede sul web."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; padding: 4px 0;")
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Codice articolo, manuale, scheda tecnica...")
        self.search_btn = QPushButton("Cerca in archivio")
        self.maxy_btn = QPushButton("Cerca sul web con Maxy")
        self.maxy_btn.setToolTip("Maxy cerca manuali e schede tecniche su internet")
        search_row.addWidget(self.search_input, stretch=1)
        search_row.addWidget(self.search_btn)
        search_row.addWidget(self.maxy_btn)
        layout.addLayout(search_row)

        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(
            r"Percorso cartella — es. C:\Manuali oppure \\server\condivisa\docs"
        )
        browse_btn = QPushButton("Sfoglia...")
        self.import_btn = QPushButton("Importa cartella")
        folder_row.addWidget(self.folder_input, stretch=1)
        folder_row.addWidget(browse_btn)
        folder_row.addWidget(self.import_btn)
        layout.addLayout(folder_row)

        self.doc_table = QTableWidget(0, 4)
        self.doc_table.setHorizontalHeaderLabels(["Codice", "Tipo", "Titolo", "Percorso / URL"])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.doc_table, stretch=2)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Dettaglio ricerca o risposta Maxy")
        layout.addWidget(self.detail, stretch=1)

        open_btn = QPushButton("Apri documento selezionato")
        open_btn.clicked.connect(self._open_selected)
        layout.addWidget(open_btn)

        self.search_btn.clicked.connect(self._search_local)
        self.search_input.returnPressed.connect(self._search_local)
        self.maxy_btn.clicked.connect(self._search_web)
        browse_btn.clicked.connect(self._browse_folder)
        self.import_btn.clicked.connect(self._import_folder)

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Seleziona cartella documenti")
        if path:
            self.folder_input.setText(path)

    def _import_folder(self) -> None:
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Importa", "Indicare un percorso cartella.")
            return
        try:
            data = self.client.import_documents_folder(folder)
        except Exception as exc:
            QMessageBox.warning(self, "Importa", str(exc))
            return

        message = (
            f"Cartella: {data.get('folder', folder)}\n"
            f"File trovati: {data.get('files_found', 0)}\n"
            f"Importati: {data.get('imported', 0)}\n"
            f"PDF indicizzati per Maxy: {data.get('pdfs_indexed', 0)}"
        )
        errors = data.get("errors") or []
        if errors:
            message += "\n\nAvvisi:\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Importazione completata", message)
        if self.search_input.text().strip():
            self._search_local()

    def _search_local(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Cerca", "Inserire un termine di ricerca.")
            return
        self._mode = "local"
        try:
            data = self.client.search_documents(query)
        except Exception as exc:
            QMessageBox.warning(self, "Cerca", str(exc))
            return
        self._fill_local_table(data)

    def _fill_local_table(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        self._web_results = []
        self.doc_table.setRowCount(len(items))
        for row, doc in enumerate(items):
            self.doc_table.setItem(row, 0, QTableWidgetItem(doc.get("internal_code", "") or ""))
            self.doc_table.setItem(row, 1, QTableWidgetItem(doc.get("doc_type", "")))
            self.doc_table.setItem(row, 2, QTableWidgetItem(doc.get("title", "")))
            url = doc.get("file_url") or doc.get("file_path") or ""
            self.doc_table.setItem(row, 3, QTableWidgetItem(url))

        chunks = data.get("pdf_chunks", [])
        chunk_lines = [
            f"• {c.get('pdf_name', '')} pag.{c.get('page', '')} — {c.get('section', '')}"
            for c in chunks
        ]
        self.detail.setPlainText(
            f"Documenti in archivio: {data.get('total', len(items))}\n"
            + ("\n".join(chunk_lines) if chunk_lines else "")
        )

    def _search_web(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Maxy", "Inserire cosa cercare (es. codice articolo o prodotto).")
            return
        self._mode = "web"
        self.maxy_btn.setEnabled(False)
        self.detail.setPlainText("Maxy sta cercando documentazione sul web...")
        try:
            data = self.client.search_documents_web(query)
        except Exception as exc:
            QMessageBox.warning(self, "Ricerca web", str(exc))
            self.detail.clear()
            return
        finally:
            self.maxy_btn.setEnabled(True)

        self._web_results = data.get("results", [])
        self.doc_table.setRowCount(len(self._web_results))
        for row, item in enumerate(self._web_results):
            self.doc_table.setItem(row, 0, QTableWidgetItem(""))
            self.doc_table.setItem(row, 1, QTableWidgetItem(item.get("doc_type", "web")))
            self.doc_table.setItem(row, 2, QTableWidgetItem(item.get("title", "")))
            self.doc_table.setItem(row, 3, QTableWidgetItem(item.get("url", "")))

        answer = data.get("answer", "")
        self.detail.setPlainText(
            f"Risultati web trovati: {len(self._web_results)}\n\n{answer}"
        )

    def _open_selected(self) -> None:
        row = self.doc_table.currentRow()
        if row < 0:
            return
        url_item = self.doc_table.item(row, 3)
        if not url_item or not url_item.text():
            return
        target = url_item.text().strip()
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
            return
        if os.path.isfile(target):
            os.startfile(target)  # noqa: S606 — Windows desktop
            return
        QMessageBox.warning(self, "Apri", f"Percorso non raggiungibile:\n{target}")
