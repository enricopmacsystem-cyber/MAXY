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
from mac_ai_assistant.branding import APP_DISPLAY_NAME
from mac_ai_assistant.credentials import load_saved_login, save_login
from mac_ai_assistant.ui.company_banner import login_footer_logo_label


class LoginDialog(QDialog):
    def __init__(self, client: HubClient, parent=None) -> None:
        super().__init__(parent)
        self.client = client
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)

        title = QLabel("Accedi con le tue credenziali EasyOne")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Usa le stesse credenziali del portale EasyOne:\n"
            "https://e.macsystem.online"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        form = QFormLayout()
        self.username = QLineEdit()
        self.username.setPlaceholderText("Utente EasyOne")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password")
        form.addRow("Utente", self.username)
        form.addRow("Password", self.password)
        layout.addLayout(form)

        self.remember_credentials = QCheckBox("Ricorda credenziali su questo PC")
        self.remember_credentials.setToolTip(
            "Salva utente e password in modo protetto (solo per questo account Windows)."
        )
        layout.addWidget(self.remember_credentials)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: #a66;")
        layout.addWidget(self.hint)
        self._load_hub_hints()
        self._load_saved_credentials()

        self.login_btn = QPushButton("Accedi")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setDefault(True)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet(
            """
            QPushButton#loginBtn {
                min-height: 40px;
                font-size: 14px;
                font-weight: bold;
                color: #f5f5f5;
                background-color: #3d3d3d;
                border: 2px solid #5a5a5a;
                border-radius: 8px;
                padding: 8px 20px;
            }
            QPushButton#loginBtn:hover {
                color: #ffffff;
                background-color: #2d4a38;
                border: 2px solid #4ade80;
            }
            QPushButton#loginBtn:pressed {
                color: #ffffff;
                background-color: #243d2f;
                border: 2px solid #22c55e;
            }
            QPushButton#loginBtn:disabled {
                color: #999999;
                background-color: #2a2a2a;
                border: 2px solid #444444;
            }
            """
        )
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()
        layout.addWidget(
            login_footer_logo_label(max_width=400, max_height=72),
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
        )

        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self._on_login)
        self.username.setFocus()

    def _load_saved_credentials(self) -> None:
        username, password, remember = load_saved_login()
        if username:
            self.username.setText(username)
        if password:
            self.password.setText(password)
        self.remember_credentials.setChecked(remember)

    def _load_hub_hints(self) -> None:
        try:
            health = self.client.health()
            if health.get("database") == "down":
                self.hint.setText(
                    "Database locale non attivo. "
                    "Installare PostgreSQL su questo PC e riavviare l'applicazione."
                )
        except Exception:
            self.hint.setText("Avvio del servizio in corso... riprovare tra qualche secondo.")

    def _on_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            QMessageBox.warning(self, "Accesso", "Inserire utente e password EasyOne.")
            return
        try:
            self.client.login(username, password)
            save_login(
                username=username,
                password=password,
                remember=self.remember_credentials.isChecked(),
            )
            self.accept()
        except Exception as exc:
            message = str(exc).strip() or "Accesso non riuscito."
            if "Credenziali" in message or "non valide" in message.lower():
                message = "Utente o password EasyOne non corretti."
            elif "non raggiungibile" in message.lower() or "connessione" in message.lower():
                message = (
                    "Servizio non raggiungibile. Verificare la connessione di rete e riprovare."
                )
            QMessageBox.warning(self, "Accesso non riuscito", message)
