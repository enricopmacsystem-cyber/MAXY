from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.ui.theme_preferences import current_tokens, style_hint_label

_POLL_MS = 4000
_CHANNEL = "generale"


class InternalChatTab(QWidget):
    """Chat interna tra colleghi connessi a Maxy AI."""

    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.client = client
        self._known_ids: set[str] = set()
        self._last_created_at: str | None = None
        self._polling = False

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(_POLL_MS)
        self._poll_timer.timeout.connect(self._poll_messages)

        layout = QVBoxLayout(self)

        header = QLabel(
            "Chat interna — canale Generale (team Mac System). "
            "I messaggi sono visibili a tutti gli utenti collegati."
        )
        header.setWordWrap(True)
        header.setProperty("hint", True)
        header.setStyleSheet(style_hint_label() + " padding: 4px 0 8px 0;")
        layout.addWidget(header)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(style_hint_label() + " font-size: 12px;")
        layout.addWidget(self.status_label)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        self.messages_view.setPlaceholderText("Nessun messaggio ancora. Scrivi il primo…")
        layout.addWidget(self.messages_view, stretch=1)
        self._apply_chat_panel_style()

        input_row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Scrivi un messaggio al team…")
        self.message_input.returnPressed.connect(self._send_message)
        self.send_btn = QPushButton("Invia")
        self.send_btn.setObjectName("primaryBtn")
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.message_input, stretch=1)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        user = client.user or {}
        name = user.get("display_name") or user.get("username") or "Operatore"
        self.status_label.setText(f"Connesso come {name}")

    def _apply_chat_panel_style(self) -> None:
        t = current_tokens()
        self.messages_view.setStyleSheet(
            f"QTextEdit {{ background: {t.surface_alt}; color: {t.text}; "
            f"border: 1px solid {t.border}; border-radius: 6px; padding: 8px; }}"
        )

    def on_tab_activated(self) -> None:
        self._apply_chat_panel_style()
        self._poll_timer.start()
        self._load_messages(full_refresh=True)

    def on_tab_deactivated(self) -> None:
        self._poll_timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.on_tab_activated()

    def hideEvent(self, event) -> None:
        self.on_tab_deactivated()
        super().hideEvent(event)

    def _send_message(self) -> None:
        text = self.message_input.text().strip()
        if not text:
            return
        self.send_btn.setEnabled(False)
        try:
            message = self.client.send_internal_chat(text, channel=_CHANNEL)
            self.message_input.clear()
            self._append_message(message)
            self._scroll_to_bottom()
        except Exception as exc:
            QMessageBox.warning(self, "Chat interna", str(exc))
        finally:
            self.send_btn.setEnabled(True)
            self.message_input.setFocus()

    def _poll_messages(self) -> None:
        if self._polling:
            return
        self._load_messages(full_refresh=False)

    def _load_messages(self, *, full_refresh: bool) -> None:
        self._polling = True
        try:
            since = None if full_refresh else self._last_created_at
            data = self.client.list_internal_chat(
                channel=_CHANNEL,
                limit=200,
                since=since,
            )
            items = data.get("items", [])
            if full_refresh:
                self._known_ids.clear()
                self.messages_view.clear()
                for item in items:
                    self._append_message(item)
            else:
                for item in items:
                    self._append_message(item)
            if items:
                self._last_created_at = items[-1].get("created_at")
            total = data.get("total", len(self._known_ids))
            self.status_label.setText(
                f"{total} messaggi nel canale Generale — aggiornamento automatico"
            )
            if items and not full_refresh:
                self._scroll_to_bottom()
        except Exception as exc:
            self.status_label.setText(f"Chat non disponibile: {exc}")
        finally:
            self._polling = False

    def _append_message(self, message: dict[str, Any]) -> None:
        msg_id = str(message.get("id", ""))
        if not msg_id or msg_id in self._known_ids:
            return
        self._known_ids.add(msg_id)

        name = html.escape(str(message.get("sender_display_name") or "Utente"))
        body = html.escape(str(message.get("body") or "")).replace("\n", "<br>")
        when = self._format_time(message.get("created_at"))
        is_mine = bool(message.get("is_mine"))

        t = current_tokens()
        if is_mine:
            block = (
                f'<div style="margin:10px 0; text-align:right;">'
                f'<span style="color:{t.text_muted}; font-size:11px;">{when} — Tu</span><br>'
                f'<span style="display:inline-block; background:{t.chat_mine_bg}; color:#fff; '
                f'padding:8px 12px; border-radius:10px; max-width:75%; text-align:left;">'
                f"{body}</span></div>"
            )
        else:
            block = (
                f'<div style="margin:10px 0; text-align:left;">'
                f'<span style="color:{t.accent}; font-weight:bold;">{name}</span> '
                f'<span style="color:{t.text_muted}; font-size:11px;">{when}</span><br>'
                f'<span style="display:inline-block; background:{t.chat_other_bg}; color:{t.text}; '
                f'padding:8px 12px; border-radius:10px; max-width:75%;">'
                f"{body}</span></div>"
            )

        cursor = self.messages_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.messages_view.setTextCursor(cursor)
        self.messages_view.insertHtml(block)

        created = message.get("created_at")
        if created:
            self._last_created_at = str(created)

    def _scroll_to_bottom(self) -> None:
        scrollbar = self.messages_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @staticmethod
    def _format_time(value: Any) -> str:
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return dt.strftime("%d/%m %H:%M")
        except ValueError:
            return str(value)[:16]
