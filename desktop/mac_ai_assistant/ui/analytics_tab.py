from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.branding import AI_ASSISTANT_NAME
from mac_ai_assistant.ui.pdf_export import export_text_to_pdf


def _percent_color(percent: float) -> QColor:
    if percent >= 30:
        return QColor("#1e7e34")
    if percent >= 15:
        return QColor("#28a745")
    if percent >= 5:
        return QColor("#5cb85c")
    return QColor("#6c757d")


def _percent_cell(value: Any) -> QTableWidgetItem:
    try:
        pct = float(value)
    except (TypeError, ValueError):
        pct = 0.0
    text = f"{pct:.1f}%"
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    color = _percent_color(pct)
    item.setBackground(color)
    item.setForeground(QColor("white"))
    item.setFont(item.font())
    return item


class AnalyticsTab(QWidget):
    """Analytics per cliente: brand, scontistica, suggerimenti Maxy."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._analytics: dict[str, Any] | None = None

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Inserisci il codice cliente EasyOne per vedere storico acquisti per brand, "
            "percentuali e scontistica applicabile. Maxy propone cosa vendere in base allo storico."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; padding: 4px 0;")
        layout.addWidget(hint)

        search_row = QHBoxLayout()
        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Codice cliente EasyOne (es. C005008)")
        self.load_btn = QPushButton("Carica analytics cliente")
        self.maxy_btn = QPushButton(f"Chiedi a {AI_ASSISTANT_NAME}")
        self.export_btn = QPushButton("Esporta PDF")
        search_row.addWidget(self.customer_input, stretch=1)
        search_row.addWidget(self.load_btn)
        search_row.addWidget(self.maxy_btn)
        search_row.addWidget(self.export_btn)
        layout.addLayout(search_row)

        self.customer_info = QLabel()
        self.customer_info.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px;")
        layout.addWidget(self.customer_info)

        splitter = QSplitter(Qt.Orientation.Vertical)

        tables = QSplitter(Qt.Orientation.Horizontal)

        brand_widget = QWidget()
        brand_layout = QVBoxLayout(brand_widget)
        brand_layout.addWidget(QLabel("Riepilogo per brand"))
        self.brand_table = QTableWidget(0, 5)
        self.brand_table.setHorizontalHeaderLabels(
            ["Brand", "Quantità", "% sul totale", "Sconto max", "Sconto consigliato"]
        )
        self.brand_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.brand_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        brand_layout.addWidget(self.brand_table)
        tables.addWidget(brand_widget)

        product_widget = QWidget()
        product_layout = QVBoxLayout(product_widget)
        product_layout.addWidget(QLabel("Prodotti acquistati"))
        self.product_table = QTableWidget(0, 8)
        self.product_table.setHorizontalHeaderLabels(
            [
                "Brand",
                "Codice",
                "Descrizione",
                "Qty",
                "% cliente",
                "% nel brand",
                "Sconto max",
                "Sconto consigliato",
            ]
        )
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        product_layout.addWidget(self.product_table)
        tables.addWidget(product_widget)

        tables.setStretchFactor(0, 2)
        tables.setStretchFactor(1, 3)
        splitter.addWidget(tables)

        self.maxy_output = QTextEdit()
        self.maxy_output.setReadOnly(True)
        self.maxy_output.setPlaceholderText(
            f"I suggerimenti di {AI_ASSISTANT_NAME} compariranno qui..."
        )
        splitter.addWidget(self.maxy_output)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, stretch=1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        self.load_btn.clicked.connect(self._load_customer)
        self.customer_input.returnPressed.connect(self._load_customer)
        self.maxy_btn.clicked.connect(self._ask_maxy)
        self.export_btn.clicked.connect(self._export_pdf)
        self.brand_table.itemSelectionChanged.connect(self._highlight_brand_products)

    def _current_code(self) -> str:
        return self.customer_input.text().strip()

    def _load_customer(self) -> None:
        code = self._current_code()
        if not code:
            QMessageBox.warning(self, "Cliente", "Inserire il codice cliente.")
            return
        try:
            data = self.client.customer_analytics(code)
        except Exception as exc:
            QMessageBox.warning(self, "Analytics", str(exc))
            return

        self._analytics = data
        name = data.get("company_name") or ""
        extra = []
        if data.get("city"):
            extra.append(data["city"])
        if data.get("sales_agent"):
            extra.append(f"Agente: {data['sales_agent']}")
        self.customer_info.setText(
            f"{code} — {name}"
            + (f"  ({' · '.join(extra)})" if extra else "")
            + f"  |  Ordini: {data.get('total_orders', 0)}"
            + f"  |  Qty totale: {data.get('total_quantity', 0)}"
        )

        brands = data.get("brands", [])
        self.brand_table.setRowCount(len(brands))
        self.product_table.setRowCount(0)
        product_rows: list[dict[str, Any]] = []

        for row, brand in enumerate(brands):
            self.brand_table.setItem(row, 0, QTableWidgetItem(str(brand.get("brand", ""))))
            self.brand_table.setItem(
                row, 1, QTableWidgetItem(str(brand.get("total_quantity", "")))
            )
            self.brand_table.setItem(row, 2, _percent_cell(brand.get("share_percent", 0)))
            self.brand_table.setItem(
                row, 3, _percent_cell(brand.get("max_discount_percent", 0))
            )
            self.brand_table.setItem(
                row, 4, _percent_cell(brand.get("suggested_discount_percent", 0))
            )
            for product in brand.get("products", []):
                product_rows.append(product)

        self.product_table.setRowCount(len(product_rows))
        for row, item in enumerate(product_rows):
            prod = item.get("product", {})
            self.product_table.setItem(row, 0, QTableWidgetItem(str(item.get("brand", ""))))
            self.product_table.setItem(
                row, 1, QTableWidgetItem(str(prod.get("internal_code", "")))
            )
            self.product_table.setItem(
                row, 2, QTableWidgetItem(str(prod.get("description", ""))[:80])
            )
            self.product_table.setItem(
                row, 3, QTableWidgetItem(str(item.get("total_quantity", "")))
            )
            self.product_table.setItem(row, 4, _percent_cell(item.get("share_percent", 0)))
            self.product_table.setItem(row, 5, _percent_cell(item.get("brand_share_percent", 0)))
            self.product_table.setItem(row, 6, _percent_cell(item.get("max_discount_percent", 0)))
            self.product_table.setItem(
                row, 7, _percent_cell(item.get("suggested_discount_percent", 0))
            )

        warnings = data.get("warnings") or []
        source = data.get("source", "local")
        status = f"Fonte dati: {source}."
        if warnings:
            status += " " + " · ".join(warnings)
        self.status_label.setText(status)
        self.maxy_output.clear()

    def _highlight_brand_products(self) -> None:
        row = self.brand_table.currentRow()
        if row < 0 or not self._analytics:
            return
        brands = self._analytics.get("brands", [])
        if row >= len(brands):
            return
        brand_name = brands[row].get("brand", "")
        for product_row in range(self.product_table.rowCount()):
            item = self.product_table.item(product_row, 0)
            if not item:
                continue
            match = item.text() == brand_name
            for col in range(self.product_table.columnCount()):
                cell = self.product_table.item(product_row, col)
                if cell:
                    cell.setBackground(QColor("#e8f4fd") if match else QColor())

    def _ask_maxy(self) -> None:
        code = self._current_code()
        if not code:
            QMessageBox.warning(self, AI_ASSISTANT_NAME, "Caricare prima un cliente.")
            return
        if not self._analytics:
            self._load_customer()
            if not self._analytics:
                return

        self.maxy_btn.setEnabled(False)
        self.maxy_output.setPlainText(f"{AI_ASSISTANT_NAME} sta analizzando lo storico cliente...")
        try:
            data = self.client.customer_maxy_suggestions(code)
        except Exception as exc:
            QMessageBox.warning(self, AI_ASSISTANT_NAME, str(exc))
            self.maxy_output.clear()
            return
        finally:
            self.maxy_btn.setEnabled(True)

        lines = [data.get("summary", "")]
        cross = data.get("cross_sell") or data.get("suggestions") or []
        if cross:
            lines.append("")
            lines.append("── Proposte cross-sell ──")
            for item in cross:
                pct = item.get("correlation_percent")
                pct_label = f" ({pct}%)" if pct is not None else ""
                lines.append(
                    f"• {item.get('internal_code')} — {item.get('description', '')[:60]}"
                    f"{pct_label}\n  {item.get('reason', '')}"
                )
        self.maxy_output.setPlainText("\n".join(lines).strip())

    def _export_pdf(self) -> None:
        if not self._analytics:
            QMessageBox.information(self, "Esporta", "Caricare prima i dati di un cliente.")
            return
        body_parts = [self.customer_info.text(), "", "=== BRAND ==="]
        for row in range(self.brand_table.rowCount()):
            cells = [
                self.brand_table.item(row, col).text()
                for col in range(self.brand_table.columnCount())
                if self.brand_table.item(row, col)
            ]
            body_parts.append(" | ".join(cells))
        body_parts.append("")
        body_parts.append("=== PRODOTTI ===")
        for row in range(self.product_table.rowCount()):
            cells = [
                self.product_table.item(row, col).text()
                for col in range(self.product_table.columnCount())
                if self.product_table.item(row, col)
            ]
            body_parts.append(" | ".join(cells))
        maxy = self.maxy_output.toPlainText().strip()
        if maxy:
            body_parts.extend(["", f"=== {AI_ASSISTANT_NAME.upper()} ===", maxy])

        code = self._current_code() or "cliente"
        export_text_to_pdf(
            self,
            title=f"Analytics cliente {code}",
            body="\n".join(body_parts),
            default_name=f"analytics_{code}",
        )
