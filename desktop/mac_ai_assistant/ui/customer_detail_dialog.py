from __future__ import annotations

import webbrowser
from typing import Any
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

def _has_web_engine() -> bool:
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

        return True
    except ImportError:
        return False


def format_customer_address(customer: dict[str, Any]) -> str:
    parts: list[str] = []
    line = (customer.get("address_line") or "").strip()
    if line:
        parts.append(line)
    cap = (customer.get("postal_code") or "").strip()
    city = (customer.get("city") or "").strip()
    province = (customer.get("province") or "").strip()
    locality = " ".join(p for p in (cap, city) if p)
    if province and province not in locality:
        locality = f"{locality} ({province})" if locality else province
    if locality:
        parts.append(locality)
    country = (customer.get("country") or "").strip()
    if country:
        parts.append(country)
    return ", ".join(parts)


def google_maps_query(customer: dict[str, Any]) -> str:
    lat = customer.get("latitude")
    lon = customer.get("longitude")
    if lat is not None and lon is not None:
        return f"{lat},{lon}"
    address = format_customer_address(customer)
    if address:
        return address
    name = (customer.get("company_name") or "").strip()
    city = (customer.get("city") or "").strip()
    return ", ".join(p for p in (name, city) if p)


def google_maps_embed_url(customer: dict[str, Any]) -> str:
    q = quote_plus(google_maps_query(customer))
    return f"https://maps.google.com/maps?q={q}&hl=it&z=15&output=embed"


def google_maps_open_url(customer: dict[str, Any]) -> str:
    q = quote_plus(google_maps_query(customer))
    return f"https://www.google.com/maps/search/?api=1&query={q}"


class CustomerDetailDialog(QDialog):
    """Popup cliente: telefono, indirizzo e mappa Google."""

    def __init__(self, customer: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._customer = customer
        code = customer.get("customer_code", "")
        name = customer.get("company_name", "")
        self.setWindowTitle(f"Cliente {code}")
        self.setMinimumSize(640, 520)
        self.resize(720, 580)

        layout = QVBoxLayout(self)

        title = QLabel(name)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        layout.addWidget(title)

        code_label = QLabel(f"Codice: {code}")
        code_label.setStyleSheet("color: #666;")
        layout.addWidget(code_label)

        phone = (customer.get("phone") or "").strip()
        phone_box = QWidget()
        phone_box.setStyleSheet(
            "background: #e8f4fd; border-radius: 8px; padding: 12px; margin: 8px 0;"
        )
        phone_layout = QVBoxLayout(phone_box)
        phone_caption = QLabel("Telefono")
        phone_caption.setStyleSheet("color: #555; font-size: 11px;")
        phone_layout.addWidget(phone_caption)
        phone_label = QLabel(phone or "Non disponibile")
        phone_font = QFont()
        phone_font.setPointSize(20)
        phone_font.setBold(True)
        phone_label.setFont(phone_font)
        phone_label.setStyleSheet("color: #0078D4;")
        phone_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        phone_layout.addWidget(phone_label)
        if phone:
            call_btn = QPushButton("Chiama / copia numero")
            call_btn.clicked.connect(lambda: self._copy_phone(phone))
            phone_layout.addWidget(call_btn)
        layout.addWidget(phone_box)

        address = format_customer_address(customer)
        addr_box = QWidget()
        addr_box.setStyleSheet(
            "background: #f8f8f8; border-radius: 8px; padding: 12px; margin: 4px 0;"
        )
        addr_layout = QVBoxLayout(addr_box)
        addr_layout.addWidget(QLabel("Indirizzo"))
        addr_text = QLabel(address or "Indirizzo non disponibile in anagrafica")
        addr_text.setWordWrap(True)
        addr_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        addr_font = QFont()
        addr_font.setPointSize(12)
        addr_text.setFont(addr_font)
        addr_layout.addWidget(addr_text)
        layout.addWidget(addr_box)

        query = google_maps_query(customer)
        if query:
            if _has_web_engine():
                from PySide6.QtWebEngineWidgets import QWebEngineView

                map_view = QWebEngineView()
                map_view.setMinimumHeight(280)
                map_view.load(QUrl(google_maps_embed_url(customer)))
                layout.addWidget(map_view, stretch=1)
            else:
                map_hint = QLabel(
                    "Anteprima mappa non disponibile in questa installazione.\n"
                    "Usa il pulsante qui sotto per aprire Google Maps."
                )
                map_hint.setWordWrap(True)
                map_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
                map_hint.setStyleSheet(
                    "background: #eee; border: 1px dashed #aaa; padding: 40px; "
                    "border-radius: 8px;"
                )
                layout.addWidget(map_hint, stretch=1)

            maps_btn = QPushButton("Apri in Google Maps")
            maps_btn.clicked.connect(self._open_maps)
            layout.addWidget(maps_btn)
        else:
            layout.addWidget(
                QLabel("Coordinate o indirizzo non sufficienti per la mappa.")
            )

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _copy_phone(self, phone: str) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(phone)
        QMessageBox.information(self, "Telefono", f"Numero copiato:\n{phone}")

    def _open_maps(self) -> None:
        url = google_maps_open_url(self._customer)
        if QDesktopServices.openUrl(QUrl(url)):
            return
        webbrowser.open(url)
