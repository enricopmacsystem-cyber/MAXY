from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt
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
from mac_ai_assistant.branding import AI_ASSISTANT_NAME
from mac_ai_assistant.export.pdf_builder import QuoteDocument, QuoteLine, build_quote_pdf
from mac_ai_assistant.ui.pdf_export import notify_export_done, suggest_pdf_path


class QuoteTab(QWidget):
    """Creazione preventivi ed esportazione PDF automatica."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._quote_counter = 1

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Compila il preventivo, aggiungi articoli dal catalogo e clicca "
                "<b>Esporta PDF</b> per generare il file automaticamente."
            )
        )

        meta_row = QHBoxLayout()
        self.quote_number = QLineEdit(self._new_quote_number())
        self.quote_number.setPlaceholderText("Numero preventivo")
        self.customer_code = QLineEdit()
        self.customer_code.setPlaceholderText("Codice cliente")
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("Ragione sociale")
        meta_row.addWidget(QLabel("N. preventivo"))
        meta_row.addWidget(self.quote_number)
        meta_row.addWidget(QLabel("Codice"))
        meta_row.addWidget(self.customer_code)
        meta_row.addWidget(QLabel("Cliente"))
        meta_row.addWidget(self.customer_name, stretch=1)
        layout.addLayout(meta_row)

        contact_row = QHBoxLayout()
        self.customer_email = QLineEdit()
        self.customer_email.setPlaceholderText("Email cliente")
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("Telefono cliente")
        self.load_customer_btn = QPushButton("Carica da EasyOne")
        contact_row.addWidget(self.customer_email)
        contact_row.addWidget(self.customer_phone)
        contact_row.addWidget(self.load_customer_btn)
        layout.addLayout(contact_row)

        add_row = QHBoxLayout()
        self.product_code = QLineEdit()
        self.product_code.setPlaceholderText("Codice articolo")
        self.add_from_catalog_btn = QPushButton("Aggiungi da catalogo")
        self.add_empty_btn = QPushButton("Riga vuota")
        self.remove_row_btn = QPushButton("Rimuovi riga")
        add_row.addWidget(self.product_code, stretch=1)
        add_row.addWidget(self.add_from_catalog_btn)
        add_row.addWidget(self.add_empty_btn)
        add_row.addWidget(self.remove_row_btn)
        layout.addLayout(add_row)

        self.lines_table = QTableWidget(0, 5)
        self.lines_table.setHorizontalHeaderLabels(
            ["Codice", "Descrizione", "Q.tà", "Prezzo unit. (EUR)", "Importo"]
        )
        self.lines_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lines_table.cellChanged.connect(self._recalc_row_total)
        layout.addWidget(self.lines_table, stretch=2)

        self.total_label = QLabel("Totale preventivo: EUR 0.00")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.total_label)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Note, condizioni di vendita, tempi di consegna...")
        self.notes.setMaximumHeight(90)
        layout.addWidget(self.notes)

        btn_row = QHBoxLayout()
        self.maxy_btn = QPushButton(f"Compila note con {AI_ASSISTANT_NAME}")
        self.export_btn = QPushButton("Esporta PDF")
        self.export_btn.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        btn_row.addWidget(self.maxy_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.export_btn)
        layout.addLayout(btn_row)

        self.load_customer_btn.clicked.connect(self._load_customer)
        self.add_from_catalog_btn.clicked.connect(self._add_from_catalog)
        self.add_empty_btn.clicked.connect(lambda: self._append_line())
        self.remove_row_btn.clicked.connect(self._remove_selected_row)
        self.product_code.returnPressed.connect(self._add_from_catalog)
        self.maxy_btn.clicked.connect(self._fill_notes_with_maxy)
        self.export_btn.clicked.connect(self._export_pdf)

    def _new_quote_number(self) -> str:
        stamp = date.today().strftime("%Y%m%d")
        number = f"PRV-{stamp}-{self._quote_counter:03d}"
        self._quote_counter += 1
        return number

    def _append_line(
        self,
        *,
        code: str = "",
        description: str = "",
        quantity: str = "1",
        unit_price: str = "0.00",
    ) -> None:
        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)
        self.lines_table.blockSignals(True)
        for col, value in enumerate([code, description, quantity, unit_price, "0.00"]):
            item = QTableWidgetItem(value)
            if col == 4:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.lines_table.setItem(row, col, item)
        self.lines_table.blockSignals(False)
        self._recalc_row_total(row, 2)

    def _remove_selected_row(self) -> None:
        row = self.lines_table.currentRow()
        if row >= 0:
            self.lines_table.removeRow(row)
            self._recalc_totals()

    def _load_customer(self) -> None:
        code = self.customer_code.text().strip()
        if not code:
            QMessageBox.information(self, "Cliente", "Inserire il codice cliente.")
            return
        try:
            data = self.client.search_customers(code)
            items = data.get("items", [])
            match = next((c for c in items if c.get("customer_code") == code), None)
            if not match and items:
                match = items[0]
            if not match:
                QMessageBox.warning(self, "Cliente", "Cliente non trovato in EasyOne.")
                return
            self.customer_name.setText(match.get("company_name", ""))
            self.customer_email.setText(match.get("email", "") or "")
            self.customer_phone.setText(match.get("phone", "") or "")
        except Exception as exc:
            QMessageBox.warning(self, "Cliente", str(exc))

    def _add_from_catalog(self) -> None:
        code = self.product_code.text().strip()
        if not code:
            return
        try:
            data = self.client.search_products(code, limit=5)
            items = data.get("items", [])
            product = None
            for item in items:
                p = item.get("product", {})
                if p.get("internal_code", "").upper() == code.upper():
                    product = p
                    break
            if not product and items:
                product = items[0].get("product", {})
            if not product:
                QMessageBox.warning(self, "Catalogo", "Articolo non trovato.")
                return
            self._append_line(
                code=product.get("internal_code", ""),
                description=product.get("description", ""),
                unit_price=str(product.get("price", "0.00")),
            )
            self.product_code.clear()
        except Exception as exc:
            QMessageBox.warning(self, "Catalogo", str(exc))

    def _recalc_row_total(self, row: int, column: int) -> None:
        if column > 3:
            return
        try:
            qty = Decimal(self._cell_text(row, 2) or "0")
            price = Decimal(self._cell_text(row, 3).replace(",", ".") or "0")
            total_item = self.lines_table.item(row, 4)
            if total_item:
                self.lines_table.blockSignals(True)
                total_item.setText(f"{qty * price:.2f}")
                self.lines_table.blockSignals(False)
        except (InvalidOperation, ValueError):
            pass
        self._recalc_totals()

    def _cell_text(self, row: int, col: int) -> str:
        item = self.lines_table.item(row, col)
        return item.text().strip() if item else ""

    def _recalc_totals(self) -> None:
        total = Decimal("0")
        for row in range(self.lines_table.rowCount()):
            try:
                total += Decimal(self._cell_text(row, 4).replace(",", ".") or "0")
            except InvalidOperation:
                continue
        self.total_label.setText(f"Totale preventivo: EUR {total:.2f}")

    def _collect_lines(self) -> list[QuoteLine]:
        lines: list[QuoteLine] = []
        for row in range(self.lines_table.rowCount()):
            code = self._cell_text(row, 0)
            desc = self._cell_text(row, 1)
            if not code and not desc:
                continue
            lines.append(
                QuoteLine(
                    code=code,
                    description=desc,
                    quantity=self._cell_text(row, 2) or "1",
                    unit_price=self._cell_text(row, 3) or "0",
                )
            )
        return lines

    def _build_document(self) -> QuoteDocument:
        return QuoteDocument(
            quote_number=self.quote_number.text().strip() or self._new_quote_number(),
            quote_date=date.today(),
            customer_name=self.customer_name.text().strip(),
            customer_code=self.customer_code.text().strip(),
            customer_email=self.customer_email.text().strip(),
            customer_phone=self.customer_phone.text().strip(),
            notes=self.notes.toPlainText().strip(),
            lines=self._collect_lines(),
        )

    def _fill_notes_with_maxy(self) -> None:
        lines = self._collect_lines()
        if not lines:
            QMessageBox.information(
                self,
                AI_ASSISTANT_NAME,
                "Aggiungere almeno una riga articolo prima di chiedere a Maxy.",
            )
            return
        summary = ", ".join(f"{line.code} x{line.quantity}" for line in lines[:8])
        question = (
            f"Scrivi note brevi per un preventivo commerciale con questi articoli: {summary}. "
            "Includi tempi di consegna indicativi e tono professionale. Max 120 parole."
        )
        try:
            data = self.client.ask_assistant(question)
            self.notes.setPlainText(data.get("answer", ""))
        except Exception as exc:
            QMessageBox.warning(self, AI_ASSISTANT_NAME, str(exc))

    def _export_pdf(self) -> None:
        document = self._build_document()
        if not document.lines:
            answer = QMessageBox.question(
                self,
                "Esporta PDF",
                "Il preventivo non contiene righe articolo. Esportare comunque?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        default_name = document.customer_code or document.customer_name or "preventivo"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva preventivo PDF",
            str(suggest_pdf_path(f"Preventivo_{default_name}")),
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            saved = build_quote_pdf(document, Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "Esporta PDF", f"Impossibile creare il PDF:\n{exc}")
            return
        notify_export_done(self, saved)
