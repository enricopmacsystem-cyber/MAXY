from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
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
from mac_ai_assistant.ui.customer_detail_dialog import (
    CustomerDetailDialog,
    format_customer_address,
)


class CustomersTab(QWidget):
    """Anagrafica clienti EasyOne — archivio locale persistente."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._all_items: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)

        hint = QLabel(
            "I clienti importati con «Sincronizza con EasyOne» restano salvati nel database "
            "locale. Doppio clic su un cliente per aprire mappa, indirizzo e telefono."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; padding: 4px 0;")
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtra per nome, codice, telefono, email...")
        self.search_btn = QPushButton("Cerca / Filtra")
        self.reload_btn = QPushButton("Mostra tutti")
        self.detail_btn = QPushButton("Scheda cliente")
        row.addWidget(self.search_input, stretch=1)
        row.addWidget(self.search_btn)
        row.addWidget(self.reload_btn)
        row.addWidget(self.detail_btn)
        layout.addLayout(row)

        self.count_label = QLabel()
        self.count_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.count_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Codice", "Ragione sociale", "Telefono", "Email", "Città"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=3)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Seleziona un cliente per i dettagli")
        layout.addWidget(self.detail, stretch=1)

        self.search_btn.clicked.connect(self._load_customers)
        self.reload_btn.clicked.connect(self._load_all)
        self.search_input.returnPressed.connect(self._load_customers)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.table.cellDoubleClicked.connect(self._open_customer_popup)
        self.detail_btn.clicked.connect(self._open_customer_popup)

        QTimer.singleShot(200, self._load_all)

    def _fill_table(self, items: list[dict[str, Any]], total: int) -> None:
        self._all_items = items
        self.table.setRowCount(len(items))
        for row, customer in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(customer.get("customer_code", "")))
            self.table.setItem(row, 1, QTableWidgetItem(customer.get("company_name", "")))
            self.table.setItem(row, 2, QTableWidgetItem(customer.get("phone", "") or ""))
            self.table.setItem(row, 3, QTableWidgetItem(customer.get("email", "") or ""))
            self.table.setItem(row, 4, QTableWidgetItem(customer.get("city", "") or ""))

        shown = len(items)
        if shown < total:
            self.count_label.setText(
                f"Clienti in archivio: {total}  (mostrati {shown} — usare il filtro per restringere)"
            )
        else:
            self.count_label.setText(f"Clienti in archivio: {total}")

        if total == 0:
            self.count_label.setText(
                "Nessun cliente in archivio. Usare «Sincronizza con EasyOne» per importare l'anagrafica."
            )

    def _load_all(self) -> None:
        self.search_input.clear()
        try:
            data = self.client.list_all_customers()
        except Exception as exc:
            QMessageBox.warning(self, "Clienti", str(exc))
            return
        self._fill_table(data.get("items", []), data.get("total", 0))

    def _load_customers(self) -> None:
        query = self.search_input.text().strip()
        try:
            data = self.client.list_all_customers(query=query)
        except Exception as exc:
            QMessageBox.warning(self, "Clienti", str(exc))
            return
        self._fill_table(data.get("items", []), data.get("total", 0))

    def _show_detail(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._all_items):
            return
        customer = self._all_items[row]
        address = format_customer_address(customer)
        lines = [
            f"Codice: {customer.get('customer_code', '')}",
            f"Ragione sociale: {customer.get('company_name', '')}",
            f"Telefono: {customer.get('phone') or '—'}",
            f"Indirizzo: {address or '—'}",
            f"Email: {customer.get('email') or '—'}",
            f"Agente: {customer.get('sales_agent') or '—'}",
            "",
            "Doppio clic per aprire mappa Google e scheda contatto.",
        ]
        self.detail.setPlainText("\n".join(lines))

    def _open_customer_popup(self, *_args) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._all_items):
            QMessageBox.information(
                self,
                "Cliente",
                "Selezionare un cliente dall'elenco.",
            )
            return
        customer = dict(self._all_items[row])
        code = customer.get("customer_code", "")
        try:
            fresh = self.client.get_customer(code)
            if fresh:
                customer = fresh
        except Exception:
            pass
        dialog = CustomerDetailDialog(customer, self)
        dialog.exec()

    def refresh_after_sync(self) -> None:
        """Richiamato dopo sync EasyOne per aggiornare l'elenco."""
        self._load_all()
