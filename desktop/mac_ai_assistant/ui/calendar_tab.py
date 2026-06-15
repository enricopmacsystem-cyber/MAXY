from __future__ import annotations



import webbrowser

from datetime import date, datetime, timedelta

from typing import Any



from PySide6.QtCore import Qt, QTimer

from PySide6.QtGui import QColor

from PySide6.QtWidgets import (

    QCheckBox,

    QGridLayout,

    QHBoxLayout,

    QHeaderView,

    QLabel,

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

from mac_ai_assistant.ui.login_dialog import LoginDialog



_OUTLOOK_COLOR = "#0078D4"

_EASYONE_COLOR = "#E67E22"

_WEEKDAY_NAMES = ("Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom")



# Intervallo caricamento appuntamenti (agenda completa)

_LOAD_PAST_DAYS = 90

_LOAD_FUTURE_DAYS = 180





def _connect_button_style(color: str, *, connected: bool) -> str:

    border = "2px solid #2ecc71" if connected else "2px solid transparent"

    return (

        f"QPushButton {{ background:{color}; color:white; border-radius:6px;"

        f" padding:8px 16px; font-weight:bold; border:{border}; }}"

        f"QPushButton:hover {{ filter: brightness(1.08); }}"

        f"QPushButton:disabled {{ background:#aaa; color:#eee; }}"

    )





class CalendarTab(QWidget):

    """Calendario unificato: EasyOne automatico + Outlook opzionale."""



    def __init__(self, client: HubClient, parent: QWidget | None = None) -> None:

        super().__init__(parent)

        self.client = client

        self._week_start = self._monday_of(date.today())

        self._events: list[dict[str, Any]] = []

        self._oauth_state: str | None = None

        self._outlook_connected = False

        self._easyone_connected = False

        self._easyone_portal_url = "https://e.macsystem.online"

        self._oauth_timer = QTimer(self)

        self._oauth_timer.setInterval(2000)

        self._oauth_timer.timeout.connect(self._poll_outlook_oauth)

        self._activate_timer = QTimer(self)
        self._activate_timer.setSingleShot(True)
        self._activate_timer.setInterval(150)
        self._activate_timer.timeout.connect(self._do_tab_activate)

        layout = QVBoxLayout(self)



        intro = QLabel(

            "L'agenda EasyOne del CRM si carica automaticamente con le credenziali usate "

            "per accedere a Maxy. Puoi collegare anche Outlook o un altro account EasyOne."

        )

        intro.setWordWrap(True)

        intro.setStyleSheet("color: #555; padding: 2px 0 8px 0;")

        layout.addWidget(intro)



        header = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Settimana precedente")

        self.next_btn = QPushButton("Settimana successiva ▶")

        self.today_btn = QPushButton("Oggi")

        self.refresh_btn = QPushButton("Aggiorna")

        self.range_label = QLabel()

        self.range_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        header.addWidget(self.prev_btn)

        header.addWidget(self.today_btn)

        header.addWidget(self.next_btn)

        header.addStretch()

        header.addWidget(self.range_label)

        header.addStretch()

        header.addWidget(self.refresh_btn)

        layout.addLayout(header)



        connect_row = QHBoxLayout()

        self.outlook_connect_btn = QPushButton("Collega Outlook")

        self.outlook_connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.outlook_connect_btn.setStyleSheet(_connect_button_style(_OUTLOOK_COLOR, connected=False))

        self.outlook_connect_btn.setToolTip(

            "Accesso opzionale al calendario Microsoft personale (OAuth)"

        )

        self.easyone_connect_btn = QPushButton("Altro account EasyOne")

        self.easyone_connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.easyone_connect_btn.setStyleSheet(_connect_button_style(_EASYONE_COLOR, connected=False))

        self.easyone_connect_btn.setToolTip(

            "Accesso opzionale con un altro utente EasyOne (sostituisce la sessione corrente)"

        )

        connect_row.addWidget(self.outlook_connect_btn)

        connect_row.addWidget(self.easyone_connect_btn)

        connect_row.addStretch()

        self.show_outlook = QCheckBox("Mostra Outlook")

        self.show_outlook.setChecked(True)

        self.show_easyone = QCheckBox("Mostra EasyOne")

        self.show_easyone.setChecked(True)

        connect_row.addWidget(self.show_outlook)

        connect_row.addWidget(self.show_easyone)

        layout.addLayout(connect_row)



        self.status_label = QLabel()

        self.status_label.setWordWrap(True)

        self.status_label.setStyleSheet("color: #555;")

        layout.addWidget(self.status_label)



        splitter = QSplitter(Qt.Orientation.Vertical)



        week_widget = QWidget()

        week_layout = QVBoxLayout(week_widget)

        week_layout.addWidget(QLabel("Vista settimanale"))

        self.week_grid = QGridLayout()

        week_container = QWidget()

        week_container.setLayout(self.week_grid)

        week_layout.addWidget(week_container)

        splitter.addWidget(week_widget)



        bottom = QSplitter(Qt.Orientation.Horizontal)

        list_widget = QWidget()

        list_layout = QVBoxLayout(list_widget)

        self.agenda_label = QLabel("Agenda unificata — tutti gli appuntamenti caricati")

        list_layout.addWidget(self.agenda_label)

        self.events_table = QTableWidget(0, 6)

        self.events_table.setHorizontalHeaderLabels(

            ["Fonte", "Data", "Ora", "Titolo", "Cliente", "Luogo"]

        )

        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        list_layout.addWidget(self.events_table)

        bottom.addWidget(list_widget)



        self.detail_view = QTextEdit()

        self.detail_view.setReadOnly(True)

        self.detail_view.setPlaceholderText("Seleziona un evento per i dettagli")

        bottom.addWidget(self.detail_view)

        bottom.setStretchFactor(0, 3)

        bottom.setStretchFactor(1, 2)

        splitter.addWidget(bottom)



        splitter.setStretchFactor(0, 2)

        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter, stretch=1)



        self.prev_btn.clicked.connect(self._prev_week)

        self.next_btn.clicked.connect(self._next_week)

        self.today_btn.clicked.connect(self._go_today)

        self.refresh_btn.clicked.connect(self._load_calendar)

        self.show_outlook.toggled.connect(self._render_views)

        self.show_easyone.toggled.connect(self._render_views)

        self.events_table.itemSelectionChanged.connect(self._show_selected_detail)

        self.outlook_connect_btn.clicked.connect(self._connect_outlook)

        self.easyone_connect_btn.clicked.connect(self._connect_easyone)



        self._refresh_connection_status()



    def on_tab_activated(self) -> None:

        """Richiamato quando l'utente apre la scheda Calendario."""

        self._activate_timer.start()

    def _do_tab_activate(self) -> None:

        self._refresh_connection_status()

        self._load_calendar()



    @staticmethod

    def _monday_of(day: date) -> date:

        return day - timedelta(days=day.weekday())



    def _week_end(self) -> date:

        return self._week_start + timedelta(days=6)



    def _load_window(self) -> tuple[datetime, datetime]:

        """Intervallo ampio per scaricare tutti gli appuntamenti rilevanti."""

        today = date.today()

        load_start = today - timedelta(days=_LOAD_PAST_DAYS)

        load_end = today + timedelta(days=_LOAD_FUTURE_DAYS)

        start_dt = datetime.combine(load_start, datetime.min.time())

        end_dt = datetime.combine(load_end + timedelta(days=1), datetime.min.time())

        return start_dt, end_dt



    def _update_range_label(self) -> None:

        end = self._week_end()

        self.range_label.setText(

            f"{self._week_start.strftime('%d/%m/%Y')} — {end.strftime('%d/%m/%Y')}"

        )



    def _prev_week(self) -> None:

        self._week_start -= timedelta(days=7)

        self._update_range_label()

        self._render_views()



    def _next_week(self) -> None:

        self._week_start += timedelta(days=7)

        self._update_range_label()

        self._render_views()



    def _go_today(self) -> None:

        self._week_start = self._monday_of(date.today())

        self._update_range_label()

        self._render_views()



    def _easyone_session_label(self) -> str:

        if not self.client.is_authenticated:

            return ""

        user = self.client.user or {}

        return str(user.get("display_name") or user.get("username") or "EasyOne")



    def _refresh_connection_status(self) -> None:

        session_easyone = self.client.is_authenticated

        try:

            status = self.client.calendar_status()

        except Exception as exc:

            self.status_label.setText(f"Stato connessioni non disponibile: {exc}")

            if session_easyone:

                self._mark_easyone_connected(self._easyone_session_label())

            return



        self._outlook_connected = bool(status.get("outlook_account_available"))

        self._easyone_connected = bool(status.get("easyone_connected")) or session_easyone

        outlook_email = status.get("outlook_email") or ""

        portal = status.get("easyone_portal_url") or "https://e.macsystem.online"

        self._easyone_portal_url = portal



        if self._outlook_connected and outlook_email:

            self.outlook_connect_btn.setText(f"Outlook — {outlook_email}")

        else:

            self.outlook_connect_btn.setText("Collega Outlook")

        self.outlook_connect_btn.setStyleSheet(

            _connect_button_style(_OUTLOOK_COLOR, connected=self._outlook_connected)

        )



        if self._easyone_connected:

            label = self._easyone_session_label() or "EasyOne attivo"

            self.easyone_connect_btn.setText(f"EasyOne — {label}")

        else:

            self.easyone_connect_btn.setText("Altro account EasyOne")

        self.easyone_connect_btn.setStyleSheet(

            _connect_button_style(_EASYONE_COLOR, connected=self._easyone_connected)

        )



        hints: list[str] = []

        if session_easyone:

            hints.append(

                f"Agenda EasyOne CRM caricata automaticamente ({self._easyone_session_label()})"

            )

        elif status.get("easyone_configured"):

            hints.append("Accedere a Maxy per visualizzare l'agenda EasyOne")



        if not status.get("outlook_configured"):

            hints.append(

                "Outlook opzionale: configurare MICROSOFT_CLIENT_ID in hub.env"

            )

        elif self._outlook_connected:

            hints.append("Outlook collegato — calendario personale importato")

        else:

            hints.append("Outlook opzionale: clic «Collega Outlook» per il calendario Microsoft")



        if status.get("needs_outlook_reconnect"):

            hints.append("Outlook: sessione scaduta — riconnettersi")

        self.status_label.setText(" · ".join(hints))



    def _mark_easyone_connected(self, label: str) -> None:

        self._easyone_connected = True

        self.easyone_connect_btn.setText(f"EasyOne — {label}")

        self.easyone_connect_btn.setStyleSheet(

            _connect_button_style(_EASYONE_COLOR, connected=True)

        )



    def _connect_outlook(self) -> None:

        try:

            status = self.client.calendar_status()

        except Exception as exc:

            QMessageBox.warning(self, "Outlook", str(exc))

            return



        if not status.get("outlook_configured"):

            QMessageBox.information(

                self,

                "Configurazione Outlook",

                "Per collegare il calendario Outlook serve la registrazione dell'app "

                "su Microsoft Entra (Azure AD).\n\n"

                "Aggiungere in hub.env:\n"

                "  MICROSOFT_CLIENT_ID=...\n"

                "  MICROSOFT_CLIENT_SECRET=...\n\n"

                "Poi riavviare il servizio MAC AI Hub.",

            )

            return



        if self._outlook_connected and not status.get("needs_outlook_reconnect"):

            reply = QMessageBox.question(

                self,

                "Outlook",

                "Outlook è già collegato.\nVuoi riconnettere l'account Microsoft?",

                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,

            )

            if reply != QMessageBox.StandardButton.Yes:

                self._load_calendar()

                return



        try:

            data = self.client.mail_oauth_start("outlook")

            self._oauth_state = data.get("state")

            auth_url = data.get("authorization_url")

            if not auth_url or not self._oauth_state:

                raise RuntimeError("Risposta OAuth incompleta dal servizio.")

            webbrowser.open(auth_url)

            self._oauth_timer.start()

            QMessageBox.information(

                self,

                "Accesso Outlook",

                "Completa l'accesso Microsoft nel browser.\n\n"

                "Autorizza l'accesso al calendario: al termine gli eventi "

                "Outlook compariranno in questa scheda.",

            )

        except Exception as exc:

            QMessageBox.warning(self, "Accesso Outlook", str(exc))



    def _poll_outlook_oauth(self) -> None:

        if not self._oauth_state:

            self._oauth_timer.stop()

            return

        try:

            result = self.client.mail_oauth_status(self._oauth_state)

        except Exception:

            return

        state = result.get("status")

        if state == "pending":

            return

        self._oauth_timer.stop()

        self._oauth_state = None

        if state == "success":

            email = result.get("email_address", "")

            QMessageBox.information(

                self,

                "Outlook collegato",

                f"Calendario Outlook collegato: {email}\n"

                "Aggiornamento eventi in corso...",

            )

            self._refresh_connection_status()

            self._load_calendar()

        elif state == "error":

            QMessageBox.warning(self, "Accesso Outlook", result.get("message", "Errore OAuth"))

        else:

            QMessageBox.warning(self, "Accesso Outlook", "Sessione OAuth scaduta. Riprovare.")



    def _connect_easyone(self) -> None:

        portal = self._easyone_portal_url

        dialog = LoginDialog(self.client, self)

        dialog.setWindowTitle("Account EasyOne personale")

        if dialog.exec() != LoginDialog.DialogCode.Accepted:

            return



        QMessageBox.information(

            self,

            "EasyOne collegato",

            f"Accesso EasyOne completato.\n"

            f"L'agenda del portale {portal} verrà aggiornata.",

        )

        self._refresh_connection_status()

        self._load_calendar()



    def _load_calendar(self) -> None:

        self._update_range_label()

        start_dt, end_dt = self._load_window()

        try:

            data = self.client.calendar_unified(

                start=start_dt.isoformat(),

                end=end_dt.isoformat(),

                include_outlook=self.show_outlook.isChecked(),

                include_easyone=self.show_easyone.isChecked(),

            )

        except Exception as exc:

            QMessageBox.warning(self, "Calendario", str(exc))

            return



        self._events = data.get("events", [])

        load_start = start_dt.date().strftime("%d/%m/%Y")

        load_end = (end_dt.date() - timedelta(days=1)).strftime("%d/%m/%Y")

        parts = [

            f"Caricati {len(self._events)} appuntamenti ({load_start} — {load_end})",

            f"Outlook: {data.get('outlook_count', 0)}",

            f"EasyOne: {data.get('easyone_count', 0)}",

        ]

        warnings = data.get("warnings") or []

        if warnings:

            parts.append(" · ".join(warnings[:2]))



        hints = self.status_label.text().split(" — ")[0].strip()

        if hints and not hints.startswith("Caricati"):

            self.status_label.setText(f"{hints} — {' | '.join(parts)}")

        else:

            self._refresh_connection_status()

            hints = self.status_label.text().strip()

            self.status_label.setText(

                f"{hints} — {' | '.join(parts)}" if hints else " | ".join(parts)

            )



        self.agenda_label.setText(

            f"Agenda unificata — {len(self._events)} appuntamenti "

            f"({load_start} — {load_end})"

        )



        if data.get("outlook_connected"):

            self._outlook_connected = True

            self.outlook_connect_btn.setStyleSheet(

                _connect_button_style(_OUTLOOK_COLOR, connected=True)

            )

        if data.get("easyone_connected") or self.client.is_authenticated:

            self._mark_easyone_connected(self._easyone_session_label() or "EasyOne")

        self._render_views()



    def _filtered_events(self) -> list[dict[str, Any]]:

        items: list[dict[str, Any]] = []

        for event in self._events:

            source = event.get("source", "")

            if source == "outlook" and not self.show_outlook.isChecked():

                continue

            if source == "easyone" and not self.show_easyone.isChecked():

                continue

            items.append(event)

        return items



    def _week_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:

        week_end = self._week_end()

        week_items: list[dict[str, Any]] = []

        for event in events:

            start_raw = event.get("start_at", "")

            try:

                start_dt = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))

            except ValueError:

                continue

            event_day = start_dt.date()

            if self._week_start <= event_day <= week_end:

                week_items.append(event)

        return week_items



    def _render_views(self) -> None:

        events = self._filtered_events()

        self._render_week_grid(self._week_events(events))

        self._render_table(events)



    def _clear_layout(self, layout: QGridLayout) -> None:

        while layout.count():

            item = layout.takeAt(0)

            widget = item.widget()

            if widget:

                widget.deleteLater()



    def _render_week_grid(self, events: list[dict[str, Any]]) -> None:

        self._clear_layout(self.week_grid)

        days = [self._week_start + timedelta(days=offset) for offset in range(7)]



        for col, day in enumerate(days):

            header = QLabel(f"{_WEEKDAY_NAMES[col]}\n{day.strftime('%d/%m')}")

            header.setAlignment(Qt.AlignmentFlag.AlignCenter)

            header.setStyleSheet("font-weight:bold; background:#f0f0f0; padding:6px;")

            self.week_grid.addWidget(header, 0, col)



        buckets: list[list[dict[str, Any]]] = [[] for _ in range(7)]

        for event in events:

            start_raw = event.get("start_at", "")

            try:

                start_dt = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00"))

            except ValueError:

                continue

            day_index = (start_dt.date() - self._week_start).days

            if 0 <= day_index < 7:

                buckets[day_index].append(event)



        for col, day_events in enumerate(buckets):

            day_events.sort(key=lambda item: item.get("start_at", ""))

            cell = QTextEdit()

            cell.setReadOnly(True)

            cell.setMinimumHeight(180)

            if not day_events:

                cell.setPlainText("—")

            else:

                lines: list[str] = []

                for event in day_events:

                    time_label = self._format_time(event.get("start_at"))

                    source = "Outlook" if event.get("source") == "outlook" else "EasyOne"

                    lines.append(f"[{time_label}] {source}")

                    lines.append(f"  {event.get('title', '')}")

                    if event.get("customer"):

                        lines.append(f"  Cliente: {event.get('customer')}")

                    lines.append("")

                cell.setPlainText("\n".join(lines).strip())

            border_color = _OUTLOOK_COLOR if col < 5 else "#999"

            cell.setStyleSheet(f"border:1px solid {border_color}; border-radius:4px;")

            self.week_grid.addWidget(cell, 1, col)



    def _render_table(self, events: list[dict[str, Any]]) -> None:

        sorted_events = sorted(events, key=lambda item: item.get("start_at", ""))

        self.events_table.setRowCount(len(sorted_events))

        for row, event in enumerate(sorted_events):

            source_label = "Outlook" if event.get("source") == "outlook" else "EasyOne"

            source_item = QTableWidgetItem(source_label)

            color = QColor(event.get("color") or _OUTLOOK_COLOR)

            source_item.setBackground(color)

            source_item.setForeground(QColor("white"))

            self.events_table.setItem(row, 0, source_item)

            self.events_table.setItem(row, 1, QTableWidgetItem(self._format_date(event.get("start_at"))))

            self.events_table.setItem(row, 2, QTableWidgetItem(self._format_time(event.get("start_at"))))

            self.events_table.setItem(row, 3, QTableWidgetItem(str(event.get("title", ""))))

            self.events_table.setItem(row, 4, QTableWidgetItem(str(event.get("customer") or "")))

            self.events_table.setItem(row, 5, QTableWidgetItem(str(event.get("location") or "")))



    def _show_selected_detail(self) -> None:

        row = self.events_table.currentRow()

        events = sorted(self._filtered_events(), key=lambda item: item.get("start_at", ""))

        if row < 0 or row >= len(events):

            return

        event = events[row]

        lines = [

            f"Fonte: {'Outlook' if event.get('source') == 'outlook' else 'EasyOne'}",

            f"Titolo: {event.get('title', '')}",

            f"Inizio: {self._format_date(event.get('start_at'))} {self._format_time(event.get('start_at'))}",

        ]

        if event.get("end_at"):

            lines.append(

                f"Fine: {self._format_date(event.get('end_at'))} {self._format_time(event.get('end_at'))}"

            )

        if event.get("customer"):

            lines.append(f"Cliente: {event.get('customer')}")

        if event.get("location"):

            lines.append(f"Luogo: {event.get('location')}")

        if event.get("description"):

            lines.append("")

            lines.append(str(event.get("description")))

        self.detail_view.setPlainText("\n".join(lines))



    @staticmethod

    def _format_date(value: Any) -> str:

        if not value:

            return ""

        try:

            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

            return dt.strftime("%d/%m/%Y")

        except ValueError:

            return str(value)[:10]



    @staticmethod

    def _format_time(value: Any) -> str:

        if not value:

            return ""

        try:

            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

            return dt.strftime("%H:%M")

        except ValueError:

            return ""


