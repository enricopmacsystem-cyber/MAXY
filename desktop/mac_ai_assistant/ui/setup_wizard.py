from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.config import AppConfig


class SetupWizard(QDialog):
    """Configurazione guidata al primo avvio (post-installazione)."""

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.result_config: AppConfig | None = None

        self.setWindowTitle("MAC AI Assistant — Configurazione iniziale")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Benvenuto in MAC AI Assistant.\n\n"
            "Configura la connessione all'Integration Hub aziendale.\n"
            "PostgreSQL, Qdrant e OpenAI sono gestiti dal server Hub — "
            "non è necessario installarli su questo PC."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.hub_url = QLineEdit(config.hub_base_url)
        self.hub_url.setPlaceholderText("http://hub.macsystem.local:8000")
        form.addRow("URL Integration Hub", self.hub_url)

        self.auth_required = QCheckBox("Richiedi login EasyOne")
        self.auth_required.setChecked(config.auth_required)
        form.addRow("", self.auth_required)
        layout.addLayout(form)

        test_btn = QPushButton("Verifica connessione Hub")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        self.status = QLabel("")
        self.status.setStyleSheet("color: gray;")
        layout.addWidget(self.status)

        save_btn = QPushButton("Salva e continua")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _test_connection(self) -> None:
        url = self.hub_url.text().strip()
        if not url:
            self.status.setText("Inserire l'URL dell'Hub.")
            return
        try:
            client = HubClient(url, timeout=8.0)
            health = client.health()
            db = health.get("database", "?")
            ver = health.get("version", "?")
            self.status.setText(f"Connessione OK — Hub v{ver}, database={db}")
            self.status.setStyleSheet("color: green;")
        except Exception as exc:
            self.status.setText(f"Connessione fallita: {exc}")
            self.status.setStyleSheet("color: red;")

    def _save(self) -> None:
        url = self.hub_url.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "URL non valido", "L'URL deve iniziare con http:// o https://")
            return
        self.result_config = AppConfig.save(
            hub_base_url=url,
            app_version=self.config.app_version,
            auth_required=self.auth_required.isChecked(),
            first_run=False,
        )
        self.accept()
