from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    _HAS_WEB_ENGINE = True
except ImportError:
    QWebEngineView = None  # type: ignore[misc, assignment]
    _HAS_WEB_ENGINE = False

QWANT_HOME = "https://www.qwant.com/?locale=it_IT"


def qwant_search_url(query: str) -> str:
    text = query.strip()
    if not text:
        return QWANT_HOME
    return f"https://www.qwant.com/?q={quote_plus(text)}&locale=it_IT"


class DashboardTab(QWidget):
    """Cruscotto: ricerca Qwant navigabile nell'app."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._web_view = None
        self._browser_layout: QVBoxLayout | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        web_section = QWidget()
        web_section.setStyleSheet(
            "QWidget#webSearchSection {"
            "  background: #f4f8fc;"
            "  border: 1px solid #c5d9eb;"
            "  border-radius: 8px;"
            "  color: #1a1a1a;"
            "}"
        )
        web_section.setObjectName("webSearchSection")
        section_layout = QVBoxLayout(web_section)
        section_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Ricerca web — Qwant")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1a3a5c;")
        section_layout.addWidget(title)

        hint = QLabel(
            "Motore di ricerca separato dalle altre funzioni. "
            "I risultati si aprono qui sotto: puoi navigare tra le pagine in tempo reale."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #333; padding-bottom: 6px;")
        section_layout.addWidget(hint)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cosa vuoi cercare sul web con Qwant...")
        self.search_btn = QPushButton("Cerca nel web")
        self.search_btn.setStyleSheet(
            "QPushButton {"
            "  background: #4a90d9; color: white; font-weight: bold;"
            "  padding: 6px 14px; border-radius: 4px; border: none;"
            "}"
            "QPushButton:hover { background: #3a7bc8; }"
        )
        search_row.addWidget(self.search_input, stretch=1)
        search_row.addWidget(self.search_btn)
        section_layout.addLayout(search_row)

        self._nav_row = QHBoxLayout()
        self.back_btn = QPushButton("Indietro")
        self.forward_btn = QPushButton("Avanti")
        self.reload_btn = QPushButton("Ricarica")
        self.home_btn = QPushButton("Qwant home")
        self.url_bar = QLineEdit()
        self.url_bar.setReadOnly(True)
        self.url_bar.setPlaceholderText("URL pagina corrente")
        for btn in (self.back_btn, self.forward_btn, self.reload_btn, self.home_btn):
            btn.setEnabled(False)
            self._nav_row.addWidget(btn)
        self._nav_row.addWidget(self.url_bar, stretch=1)
        section_layout.addLayout(self._nav_row)

        self._browser_host = QWidget()
        self._browser_layout = QVBoxLayout(self._browser_host)
        self._browser_layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel(
            "Inserisci una ricerca e premi «Cerca nel web» per aprire Qwant qui."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #444; background: #fff; border: 1px dashed #bbb;"
            "padding: 32px; border-radius: 6px; min-height: 280px;"
        )
        self._browser_layout.addWidget(self._placeholder)
        section_layout.addWidget(self._browser_host, stretch=1)

        self.search_btn.clicked.connect(self._run_search)
        self.search_input.returnPressed.connect(self._run_search)
        self.back_btn.clicked.connect(self._nav_back)
        self.forward_btn.clicked.connect(self._nav_forward)
        self.reload_btn.clicked.connect(self._nav_reload)
        self.home_btn.clicked.connect(self._go_home)

        layout.addWidget(web_section, stretch=1)

    def _ensure_web_view(self) -> bool:
        if self._web_view is not None:
            return True
        if not _HAS_WEB_ENGINE or QWebEngineView is None:
            return False
        if self._browser_layout is None:
            return False

        while self._browser_layout.count():
            item = self._browser_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._web_view = QWebEngineView()
        self._web_view.setMinimumHeight(360)
        self._browser_layout.addWidget(self._web_view)
        self._web_view.urlChanged.connect(self._on_url_changed)
        self._web_view.loadFinished.connect(self._update_nav_buttons)

        for btn in (self.back_btn, self.forward_btn, self.reload_btn, self.home_btn):
            btn.setEnabled(True)

        return True

    def _run_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.information(
                self,
                "Ricerca web",
                "Inserisci una parola o una frase da cercare con Qwant.",
            )
            return
        url = QUrl(qwant_search_url(query))
        if self._ensure_web_view():
            self._web_view.setUrl(url)
            return
        if QDesktopServices.openUrl(url):
            return
        webbrowser.open(url.toString())

    def _go_home(self) -> None:
        url = QUrl(QWANT_HOME)
        if self._ensure_web_view():
            self._web_view.setUrl(url)
        else:
            QDesktopServices.openUrl(url)

    def _nav_back(self) -> None:
        if self._web_view:
            self._web_view.back()

    def _nav_forward(self) -> None:
        if self._web_view:
            self._web_view.forward()

    def _nav_reload(self) -> None:
        if self._web_view:
            self._web_view.reload()

    def _on_url_changed(self, url: QUrl) -> None:
        self.url_bar.setText(url.toString())

    def _update_nav_buttons(self) -> None:
        if not self._web_view:
            return
        history = self._web_view.history()
        self.back_btn.setEnabled(history.canGoBack())
        self.forward_btn.setEnabled(history.canGoForward())
