from __future__ import annotations

import base64
import webbrowser
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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

_GMAIL_COLOR = "#D93025"
_GMAIL_HOVER = "#C5221F"
_OUTLOOK_COLOR = "#0078D4"
_OUTLOOK_HOVER = "#106EBE"


def _oauth_button_style(color: str, hover_color: str, *, connected: bool = False) -> str:
    border = "2px solid #2ecc71" if connected else "2px solid transparent"
    return (
        f"QPushButton {{ background-color: {color}; color: #ffffff; border: {border};"
        f" border-radius: 6px; padding: 10px 18px; font-weight: bold; font-size: 13px; }}"
        f"QPushButton:hover {{ background-color: {hover_color}; color: #ffffff; }}"
        f"QPushButton:pressed {{ background-color: {hover_color}; color: #ffffff; }}"
    )


class MailTab(QWidget):
    """Sezione cruscotto per posta Gmail / Outlook."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._accounts: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = []
        self._attachments: list[dict[str, str]] = []
        self._oauth_state: str | None = None
        self._gmail_configured = False
        self._outlook_configured = False
        self._oauth_timer = QTimer(self)
        self._oauth_timer.setInterval(2000)
        self._oauth_timer.timeout.connect(self._poll_oauth)

        layout = QVBoxLayout(self)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #555; padding: 4px;")
        layout.addWidget(self.info_label)

        top_row = QHBoxLayout()
        self.gmail_btn = QPushButton("Accedi con Gmail")
        self.gmail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gmail_btn.setStyleSheet(_oauth_button_style(_GMAIL_COLOR, _GMAIL_HOVER))
        self.outlook_btn = QPushButton("Accedi con Outlook")
        self.outlook_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.outlook_btn.setStyleSheet(_oauth_button_style(_OUTLOOK_COLOR, _OUTLOOK_HOVER))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(260)
        self.disconnect_btn = QPushButton("Scollega")
        self.refresh_btn = QPushButton("Aggiorna posta")
        top_row.addWidget(self.gmail_btn)
        top_row.addWidget(self.outlook_btn)
        top_row.addWidget(self.account_combo, stretch=1)
        top_row.addWidget(self.disconnect_btn)
        top_row.addWidget(self.refresh_btn)
        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Posta in arrivo"))
        self.inbox_table = QTableWidget(0, 4)
        self.inbox_table.setHorizontalHeaderLabels(["Da", "Oggetto", "Data", ""])
        self.inbox_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.inbox_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.inbox_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        left_layout.addWidget(self.inbox_table)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Messaggio selezionato"))
        self.message_view = QTextEdit()
        self.message_view.setReadOnly(True)
        right_layout.addWidget(self.message_view, stretch=2)

        right_layout.addWidget(QLabel("Nuovo messaggio"))
        compose_form = QHBoxLayout()
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("Destinatario")
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Oggetto")
        compose_form.addWidget(self.to_input)
        compose_form.addWidget(self.subject_input)
        right_layout.addLayout(compose_form)

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Scrivi il messaggio...")
        self.body_input.setMaximumHeight(140)
        right_layout.addWidget(self.body_input)

        attach_row = QHBoxLayout()
        self.attach_label = QLabel("Nessun allegato")
        self.attach_btn = QPushButton("Aggiungi allegati")
        self.send_btn = QPushButton("Invia")
        attach_row.addWidget(self.attach_label, stretch=1)
        attach_row.addWidget(self.attach_btn)
        attach_row.addWidget(self.send_btn)
        right_layout.addLayout(attach_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, stretch=1)

        self.gmail_btn.clicked.connect(lambda: self._start_oauth("gmail"))
        self.outlook_btn.clicked.connect(lambda: self._start_oauth("outlook"))
        self.disconnect_btn.clicked.connect(self._disconnect_account)
        self.refresh_btn.clicked.connect(self._refresh_inbox)
        self.inbox_table.itemSelectionChanged.connect(self._load_selected_message)
        self.attach_btn.clicked.connect(self._pick_attachments)
        self.send_btn.clicked.connect(self._send_mail)

        self._load_initial_state()

    def _load_initial_state(self) -> None:
        try:
            status = self.client.mail_provider_status()
            self._gmail_configured = bool(status.get("gmail_configured"))
            self._outlook_configured = bool(status.get("outlook_configured"))
            parts = []
            if self._gmail_configured:
                parts.append("Gmail pronto — clicca il pulsante rosso per accedere")
            else:
                parts.append(
                    "Gmail: configurare GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET in hub.env "
                    "(il pulsante resta utilizzabile per le istruzioni)"
                )
            if self._outlook_configured:
                parts.append("Outlook pronto — clicca il pulsante blu per accedere")
            else:
                parts.append(
                    "Outlook: configurare MICROSOFT_CLIENT_ID e MICROSOFT_CLIENT_SECRET in hub.env"
                )
            self.info_label.setText(" · ".join(parts))
            self._reload_accounts()
            self._update_oauth_button_styles()
        except Exception as exc:
            self.info_label.setText(f"Servizio posta non disponibile: {exc}")

    def _has_provider_account(self, provider: str) -> bool:
        return any(
            str(account.get("provider", "")).lower() == provider
            for account in self._accounts
        )

    def _update_oauth_button_styles(self) -> None:
        self.gmail_btn.setStyleSheet(
            _oauth_button_style(
                _GMAIL_COLOR,
                _GMAIL_HOVER,
                connected=self._has_provider_account("gmail"),
            )
        )
        self.outlook_btn.setStyleSheet(
            _oauth_button_style(
                _OUTLOOK_COLOR,
                _OUTLOOK_HOVER,
                connected=self._has_provider_account("outlook"),
            )
        )

    def _reload_accounts(self) -> None:
        self.account_combo.clear()
        try:
            self._accounts = self.client.mail_list_accounts()
        except Exception as exc:
            self._accounts = []
            QMessageBox.warning(self, "Posta", str(exc))
            return
        for account in self._accounts:
            label = f"{account.get('provider', '').upper()} — {account.get('email_address', '')}"
            self.account_combo.addItem(label, account.get("id"))
        self._update_oauth_button_styles()
        if self._accounts:
            self._refresh_inbox()

    def _current_account_id(self) -> str | None:
        value = self.account_combo.currentData()
        return str(value) if value else None

    def _start_oauth(self, provider: str) -> None:
        if provider == "gmail" and not self._gmail_configured:
            QMessageBox.information(
                self,
                "Configurazione Gmail",
                "Per collegare Gmail serve registrare l'app su Google Cloud Console.\n\n"
                "Aggiungere in hub.env (%APPDATA%\\MAC AI Assistant\\hub.env):\n"
                "  GMAIL_CLIENT_ID=...\n"
                "  GMAIL_CLIENT_SECRET=...\n"
                "  MAIL_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/mail/oauth/callback\n\n"
                "Poi riavviare il servizio MAC AI Hub.",
            )
            return
        if provider == "outlook" and not self._outlook_configured:
            QMessageBox.information(
                self,
                "Configurazione Outlook",
                "Per collegare Outlook serve registrare l'app su Microsoft Entra (Azure AD).\n\n"
                "Aggiungere in hub.env:\n"
                "  MICROSOFT_CLIENT_ID=...\n"
                "  MICROSOFT_CLIENT_SECRET=...\n"
                "  MAIL_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/mail/oauth/callback\n\n"
                "Poi riavviare il servizio MAC AI Hub.",
            )
            return

        try:
            data = self.client.mail_oauth_start(provider)
            self._oauth_state = data.get("state")
            auth_url = data.get("authorization_url")
            if not auth_url or not self._oauth_state:
                raise RuntimeError("Risposta OAuth incompleta dal servizio.")
            webbrowser.open(auth_url)
            self._oauth_timer.start()
            provider_label = "Google" if provider == "gmail" else "Microsoft"
            QMessageBox.information(
                self,
                "Accesso posta",
                f"Completa l'accesso {provider_label} nel browser.\n\n"
                "Al termine la posta comparirà automaticamente in questa scheda.",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Accesso posta", str(exc))

    def _poll_oauth(self) -> None:
        if not self._oauth_state:
            self._oauth_timer.stop()
            return
        try:
            status = self.client.mail_oauth_status(self._oauth_state)
        except Exception:
            return
        state = status.get("status")
        if state == "pending":
            return
        self._oauth_timer.stop()
        self._oauth_state = None
        if state == "success":
            email = status.get("email_address", "")
            QMessageBox.information(self, "Posta collegata", f"Account collegato: {email}")
            self._reload_accounts()
            self._update_oauth_button_styles()
            self._refresh_inbox()
        elif state == "error":
            QMessageBox.warning(self, "Accesso posta", status.get("message", "Errore OAuth"))
        else:
            QMessageBox.warning(self, "Accesso posta", "Sessione OAuth scaduta. Riprovare.")

    def _disconnect_account(self) -> None:
        account_id = self._current_account_id()
        if not account_id:
            return
        try:
            self.client.mail_disconnect_account(account_id)
            self._reload_accounts()
            self.inbox_table.setRowCount(0)
            self.message_view.clear()
        except Exception as exc:
            QMessageBox.warning(self, "Posta", str(exc))

    def _refresh_inbox(self) -> None:
        account_id = self._current_account_id()
        if not account_id:
            return
        try:
            data = self.client.mail_list_messages(account_id)
            self._messages = data.get("messages", [])
        except Exception as exc:
            QMessageBox.warning(self, "Posta", str(exc))
            return

        self.inbox_table.setRowCount(len(self._messages))
        for row, message in enumerate(self._messages):
            from_label = message.get("from_name") or message.get("from_address", "")
            subject = message.get("subject", "")
            received = message.get("received_at", "")
            if received and "T" in str(received):
                received = str(received).replace("T", " ")[:16]
            read_flag = "" if message.get("is_read", True) else "●"
            self.inbox_table.setItem(row, 0, QTableWidgetItem(from_label))
            self.inbox_table.setItem(row, 1, QTableWidgetItem(subject))
            self.inbox_table.setItem(row, 2, QTableWidgetItem(str(received)))
            self.inbox_table.setItem(row, 3, QTableWidgetItem(read_flag))

    def _load_selected_message(self) -> None:
        row = self.inbox_table.currentRow()
        account_id = self._current_account_id()
        if row < 0 or not account_id or row >= len(self._messages):
            return
        message = self._messages[row]
        message_id = message.get("id")
        if not message_id:
            return
        try:
            detail = self.client.mail_get_message(account_id, message_id)
        except Exception as exc:
            QMessageBox.warning(self, "Posta", str(exc))
            return

        lines = [
            f"Da: {detail.get('from_name') or detail.get('from_address', '')}",
            f"Oggetto: {detail.get('subject', '')}",
            "",
            detail.get("body_text") or detail.get("body_html") or "",
        ]
        attachments = detail.get("attachments") or []
        if attachments:
            lines.append("\nAllegati: " + ", ".join(attachments))
        self.message_view.setPlainText("\n".join(lines))

        from_addr = detail.get("from_address", "")
        if from_addr:
            self.to_input.setText(from_addr)
        self.subject_input.setText(f"Re: {detail.get('subject', '')}")

    def _pick_attachments(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona allegati")
        if not paths:
            return
        self._attachments = []
        for path in paths:
            file_path = Path(path)
            content = base64.b64encode(file_path.read_bytes()).decode("ascii")
            self._attachments.append(
                {
                    "filename": file_path.name,
                    "content_type": "application/octet-stream",
                    "content_base64": content,
                }
            )
        names = ", ".join(item["filename"] for item in self._attachments)
        self.attach_label.setText(names or "Nessun allegato")

    def _send_mail(self) -> None:
        account_id = self._current_account_id()
        to_addr = self.to_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_input.toPlainText().strip()
        if not account_id:
            QMessageBox.warning(self, "Posta", "Collegare un account Gmail o Outlook.")
            return
        if not to_addr or not subject or not body:
            QMessageBox.warning(self, "Posta", "Compilare destinatario, oggetto e messaggio.")
            return
        try:
            self.client.mail_send(
                account_id,
                to=to_addr,
                subject=subject,
                body=body,
                attachments=self._attachments,
            )
            QMessageBox.information(self, "Posta", "Messaggio inviato.")
            self.body_input.clear()
            self._attachments = []
            self.attach_label.setText("Nessun allegato")
        except Exception as exc:
            QMessageBox.warning(self, "Posta", str(exc))
