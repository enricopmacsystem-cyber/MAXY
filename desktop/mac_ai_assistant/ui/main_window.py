from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.branding import AI_ASSISTANT_NAME, app_icon_path, window_title
from mac_ai_assistant.ui.about_dialog import AboutDialog
from mac_ai_assistant.config import AppConfig
from mac_ai_assistant.ui.company_banner import header_logo_label
from mac_ai_assistant.ui.dashboard_tab import DashboardTab
from mac_ai_assistant.ui.internal_chat_tab import InternalChatTab
from mac_ai_assistant.ui.analytics_tab import AnalyticsTab
from mac_ai_assistant.ui.customers_tab import CustomersTab
from mac_ai_assistant.ui.calendar_tab import CalendarTab
from mac_ai_assistant.ui.documents_tab import DocumentsTab
from mac_ai_assistant.ui.macsystem_software_tab import MacSystemSoftwareTab
from mac_ai_assistant.ui.mail_tab import MailTab
from mac_ai_assistant.ui.pdf_export import export_text_to_pdf
from mac_ai_assistant.ui.quote_tab import QuoteTab
from mac_ai_assistant.ui.theme_preferences import (
    load_theme_id,
    refresh_widget_tree,
    set_theme,

)
from mac_ai_assistant.ui.themes import THEME_LABELS, ThemeId


class _AssistantRequestWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        client: HubClient,
        question: str,
        *,
        mode: str,
        history: list[dict[str, str]] | None,
    ) -> None:
        super().__init__()
        self._client = client
        self._question = question
        self._mode = mode
        self._history = history

    def run(self) -> None:
        try:
            data = self._client.ask_assistant(
                self._question,
                mode=self._mode,
                history=self._history,
            )
            self.finished.emit(data)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, client: HubClient, config: AppConfig) -> None:
        super().__init__()
        self.client = client
        self.config = config
        self.setWindowTitle(window_title())
        self.resize(1200, 800)
        icon = app_icon_path()
        if icon:
            self.setWindowIcon(QIcon(str(icon)))

        user_name = (client.user or {}).get("display_name", "Operatore")
        self._status_user = f"Connesso come {user_name}"
        self.statusBar().showMessage(self._status_user)

        central = QWidget()
        central.setObjectName("centralRoot")
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(8, 4, 8, 0)

        toolbar_row = QHBoxLayout()
        toolbar_row.addWidget(header_logo_label(max_size=48))
        toolbar_row.addStretch()
        self.sync_btn = QPushButton("Sincronizza con EasyOne")
        self.sync_btn.setObjectName("primaryBtn")
        self.sync_btn.setToolTip(
            "Importa da EasyOne articoli, giacenze, clienti e ordini "
            "nel database locale (catalogo, magazzino, analytics, Maxy)."
        )
        self.sync_btn.clicked.connect(self._sync_easyone)
        toolbar_row.addWidget(self.sync_btn)
        about_btn = QPushButton("About")
        about_btn.setFixedWidth(72)
        about_btn.setToolTip("Informazioni sul programma")
        about_btn.clicked.connect(self._show_about)
        toolbar_row.addWidget(about_btn)
        central_layout.addLayout(toolbar_row)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMouseTracking(True)
        self.tabs.tabBar().setMouseTracking(True)
        central_layout.addWidget(self.tabs)
        self.setCentralWidget(central)

        self._build_dashboard_tab()
        self._build_catalog_tab()
        self._build_customers_tab()
        self._build_warehouse_tab()
        self._build_documents_tab()
        self._build_assistant_tab()
        self._build_internal_chat_tab()
        self._build_analytics_tab()
        self._build_whatsapp_tab()
        self._build_mail_tab()
        self._build_calendar_tab()
        self._build_macsystem_software_tab()
        self._build_quote_tab()

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._build_menu()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Sistema")
        sync_action = QAction("Sincronizza con EasyOne", self)
        sync_action.triggered.connect(self._sync_easyone)
        menu.addAction(sync_action)

        theme_menu = menu.addMenu("Tema")
        self._theme_actions: dict[ThemeId, QAction] = {}
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        current = load_theme_id()
        for theme_id in ThemeId:
            label = THEME_LABELS[theme_id]
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(theme_id == current)
            action.triggered.connect(lambda _checked=False, tid=theme_id: self._apply_theme(tid))
            theme_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[theme_id] = action

        about_action = QAction("Informazioni su Maxy AI…", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)
        logout_action = QAction("Esci", self)
        logout_action.triggered.connect(self.close)
        menu.addAction(logout_action)

    def _apply_theme(self, theme_id: ThemeId) -> None:
        app = QApplication.instance()
        if app is None:
            return
        set_theme(app, theme_id)
        refresh_widget_tree(self)
        label = THEME_LABELS.get(theme_id, str(theme_id))
        self.statusBar().showMessage(f"Tema applicato: {label}", 4000)

    def _search_tab(
        self,
        title: str,
        placeholder: str,
        handler,
    ) -> tuple[QWidget, QLineEdit, QTableWidget, QTextEdit]:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        row = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText(placeholder)
        search_btn = QPushButton("Cerca")
        row.addWidget(search_input)
        row.addWidget(search_btn)
        layout.addLayout(row)

        table = QTableWidget(0, 5)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table, stretch=3)

        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setPlaceholderText(f"Dettaglio {title}")
        layout.addWidget(detail, stretch=2)

        def run_search() -> None:
            query = search_input.text().strip()
            if not query:
                return
            try:
                handler(query, table, detail)
            except Exception as exc:
                QMessageBox.warning(self, "Errore", str(exc))

        search_btn.clicked.connect(run_search)
        search_input.returnPressed.connect(run_search)
        return widget, search_input, table, detail

    def _build_dashboard_tab(self) -> None:
        self.tabs.addTab(DashboardTab(), "Cruscotto")

    def _build_catalog_tab(self) -> None:
        def handler(query: str, table: QTableWidget, detail: QTextEdit) -> None:
            data = self.client.search_products(query)
            items = data.get("items", [])
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(
                ["Codice", "Produttore", "Categoria", "Prezzo", "Disp."]
            )
            table.setRowCount(len(items))
            for row, item in enumerate(items):
                product = item.get("product", {})
                table.setItem(row, 0, QTableWidgetItem(product.get("internal_code", "")))
                table.setItem(row, 1, QTableWidgetItem(product.get("manufacturer", "")))
                table.setItem(row, 2, QTableWidgetItem(product.get("category", "")))
                table.setItem(row, 3, QTableWidgetItem(str(product.get("price", ""))))
                table.setItem(row, 4, QTableWidgetItem(str(product.get("availability", ""))))

            lines = [f"Trovati {data.get('total', len(items))} articoli\n"]
            for item in items[:5]:
                p = item.get("product", {})
                compat = item.get("compatibility", {})
                lines.append(f"• {p.get('internal_code')} — {p.get('description', '')[:80]}")
                acc = compat.get("accessories", [])
                if acc:
                    lines.append(
                        "  Accessori: "
                        + ", ".join(a["product"]["internal_code"] for a in acc[:3])
                    )
            detail.setPlainText("\n".join(lines))

        widget, _, _, _ = self._search_tab(
            "catalogo", "Cerca articolo per codice o descrizione...", handler
        )
        self.tabs.addTab(widget, "Catalogo")

    def _build_customers_tab(self) -> None:
        self.customers_tab = CustomersTab(self.client)
        self.tabs.addTab(self.customers_tab, "Clienti")

    def _build_warehouse_tab(self) -> None:
        def handler(query: str, table: QTableWidget, detail: QTextEdit) -> None:
            data = self.client.search_warehouse(query)
            items = data.get("items", [])
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(
                ["Codice", "Produttore", "Giacenza", "Stato", "Fonte"]
            )
            table.setRowCount(len(items))
            lines = []
            for row, item in enumerate(items):
                p = item.get("product", {})
                av = item.get("availability", {})
                table.setItem(row, 0, QTableWidgetItem(p.get("internal_code", "")))
                table.setItem(row, 1, QTableWidgetItem(p.get("manufacturer", "")))
                table.setItem(row, 2, QTableWidgetItem(str(av.get("quantity", ""))))
                table.setItem(row, 3, QTableWidgetItem(av.get("status_label", "")))
                table.setItem(row, 4, QTableWidgetItem(item.get("source", "")))
                lines.append(
                    f"{p.get('internal_code')}: {av.get('status_label')} ({av.get('quantity')} pz)"
                )
            detail.setPlainText("\n".join(lines))

        widget, _, _, _ = self._search_tab(
            "magazzino", "Cerca disponibilità articolo...", handler
        )
        self.tabs.addTab(widget, "Magazzino")

    def _build_documents_tab(self) -> None:
        self.tabs.addTab(DocumentsTab(self.client), "Documenti")

    def _build_assistant_tab(self) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self._technical_history: list[dict[str, str]] = []

        self._ai_mode = "commercial"

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        self.ai_mode_commercial_btn = QPushButton("Commerciale / magazzino")
        self.ai_mode_commercial_btn.setObjectName("aiModeBtn")
        self.ai_mode_commercial_btn.setCheckable(True)
        self.ai_mode_commercial_btn.setChecked(True)
        self.ai_mode_commercial_btn.setToolTip(
            "Disponibilità, catalogo, clienti e suggerimenti commerciali"
        )

        self.ai_mode_technical_btn = QPushButton("Supporto tecnico · manuali")
        self.ai_mode_technical_btn.setObjectName("aiModeBtn")
        self.ai_mode_technical_btn.setCheckable(True)
        self.ai_mode_technical_btn.setToolTip(
            "Risposte dai manuali tecnici Dahua, RISCO, ELMO, NOTIFIER, ESSER"
        )

        self._ai_mode_group = QButtonGroup(widget)
        self._ai_mode_group.setExclusive(True)
        self._ai_mode_group.addButton(self.ai_mode_commercial_btn)
        self._ai_mode_group.addButton(self.ai_mode_technical_btn)
        self.ai_mode_commercial_btn.clicked.connect(
            lambda: self._set_ai_mode("commercial")
        )
        self.ai_mode_technical_btn.clicked.connect(
            lambda: self._set_ai_mode("technical")
        )

        mode_row.addWidget(self.ai_mode_commercial_btn, stretch=1)
        mode_row.addWidget(self.ai_mode_technical_btn, stretch=1)

        self.clear_chat_btn = QPushButton("Nuova conversazione")
        self.clear_chat_btn.clicked.connect(self._reset_technical_chat)
        self.clear_chat_btn.setVisible(False)
        mode_row.addWidget(self.clear_chat_btn)
        layout.addLayout(mode_row)

        self.ai_input = QTextEdit()
        self.ai_input.setObjectName("aiInput")
        self.ai_input.setPlaceholderText(
            f"Chiedi a {AI_ASSISTANT_NAME}: es. RT-AX58U disponibilità e accessori compatibili?"
        )
        self.ai_input.setMaximumHeight(100)
        layout.addWidget(self.ai_input)

        ask_row = QHBoxLayout()
        self.ai_ask_btn = QPushButton(f"Chiedi a {AI_ASSISTANT_NAME}")
        export_ai_btn = QPushButton("Esporta PDF")
        ask_row.addWidget(self.ai_ask_btn)
        ask_row.addWidget(export_ai_btn)
        layout.addLayout(ask_row)

        self._ai_thread: QThread | None = None
        self._ai_worker: _AssistantRequestWorker | None = None

        self.ai_output = QTextEdit()
        self.ai_output.setObjectName("aiOutput")
        self.ai_output.setReadOnly(True)
        layout.addWidget(self.ai_output)

        def ask() -> None:
            q = self.ai_input.toPlainText().strip()
            if not q or self._ai_thread is not None:
                return
            mode = self._ai_mode
            history = list(self._technical_history) if mode == "technical" else None
            self._pending_ai_question = q
            self._pending_ai_mode = mode
            if mode == "technical":
                self.ai_output.setPlainText(
                    "Ricerca nei manuali in corso…\n\n"
                    "L'app resta utilizzabile: la risposta può richiedere 1–2 minuti."
                )
            else:
                self.ai_output.setPlainText("Elaborazione in corso…")
            self._set_ai_busy(True)

            self._ai_thread = QThread()
            self._ai_worker = _AssistantRequestWorker(
                self.client, q, mode=mode, history=history
            )
            self._ai_worker.moveToThread(self._ai_thread)
            self._ai_thread.started.connect(self._ai_worker.run)
            self._ai_worker.finished.connect(self._on_ai_answer)
            self._ai_worker.failed.connect(self._on_ai_error)
            self._ai_worker.finished.connect(self._ai_thread.quit)
            self._ai_worker.failed.connect(self._ai_thread.quit)
            self._ai_thread.finished.connect(self._cleanup_ai_thread)
            self._ai_thread.start()

        def export_ai_pdf() -> None:
            export_text_to_pdf(
                self,
                title=f"Risposta {AI_ASSISTANT_NAME}",
                body=self.ai_output.toPlainText(),
                default_name=f"maxy_risposta",
                subtitle=self.ai_input.toPlainText().strip()[:120] or None,
            )

        self.ai_ask_btn.clicked.connect(ask)
        export_ai_btn.clicked.connect(export_ai_pdf)
        self.tabs.addTab(widget, AI_ASSISTANT_NAME)

    def _set_ai_busy(self, busy: bool) -> None:
        self.ai_ask_btn.setEnabled(not busy)
        self.ai_mode_commercial_btn.setEnabled(not busy)
        self.ai_mode_technical_btn.setEnabled(not busy)
        if busy:
            self.statusBar().showMessage(
                f"{AI_ASSISTANT_NAME}: elaborazione in corso… (l'app resta utilizzabile)"
            )
        else:
            self.statusBar().showMessage(self._status_user)

    def _cleanup_ai_thread(self) -> None:
        if self._ai_worker is not None:
            self._ai_worker.deleteLater()
            self._ai_worker = None
        if self._ai_thread is not None:
            self._ai_thread.deleteLater()
            self._ai_thread = None

    def _format_ai_answer(self, data: dict[str, object], mode: str) -> str:
        parts = [str(data.get("answer", ""))]
        if data.get("mode") == "technical":
            sources = data.get("technical_sources") or []
            if sources:
                parts.append("\n\nFonti:")
                for src in sources[:12]:
                    parts.append(f"  • {src}")
        else:
            if data.get("article"):
                a = data["article"]
                if isinstance(a, dict):
                    parts.append(
                        f"\nArticolo: {a.get('internal_code')} — {a.get('manufacturer')}"
                    )
            if data.get("availability"):
                av = data["availability"]
                if isinstance(av, dict):
                    parts.append(f"Disponibilità: {av.get('status_label')}")
            suggestions = data.get("commercial_suggestions", [])
            if suggestions and isinstance(suggestions, list):
                parts.append("\nSuggerimenti:")
                for s in suggestions[:5]:
                    if isinstance(s, dict):
                        parts.append(f"  • {s.get('internal_code')}: {s.get('reason')}")
        return "\n".join(parts)

    def _on_ai_answer(self, data: dict) -> None:
        q = getattr(self, "_pending_ai_question", "")
        mode = getattr(self, "_pending_ai_mode", self._ai_mode)
        self.ai_output.setPlainText(self._format_ai_answer(data, mode))
        if mode == "technical":
            self._technical_history.append({"role": "user", "content": q})
            self._technical_history.append(
                {"role": "assistant", "content": str(data.get("answer", ""))}
            )
            if len(self._technical_history) > 12:
                self._technical_history = self._technical_history[-12:]
        self.ai_input.clear()
        self._set_ai_busy(False)

    def _on_ai_error(self, message: str) -> None:
        self._set_ai_busy(False)
        QMessageBox.warning(self, f"Errore {AI_ASSISTANT_NAME}", message)

    def _set_ai_mode(self, mode: str) -> None:
        if mode not in ("commercial", "technical"):
            return
        if mode == self._ai_mode:
            return
        self._ai_mode = mode
        self._on_ai_mode_changed()

    def _on_ai_mode_changed(self) -> None:
        mode = self._ai_mode
        self.ai_mode_commercial_btn.setChecked(mode == "commercial")
        self.ai_mode_technical_btn.setChecked(mode == "technical")
        self.clear_chat_btn.setVisible(mode == "technical")

        if mode == "technical":
            self.ai_input.setPlaceholderText(
                "Supporto tecnico: es. quale eyeball Dahua ha audio bidirezionale?"
            )
        else:
            self.ai_input.setPlaceholderText(
                f"Chiedi a {AI_ASSISTANT_NAME}: es. RT-AX58U disponibilità e accessori compatibili?"
            )
        self.ai_output.clear()

    def _reset_technical_chat(self) -> None:
        self._technical_history.clear()
        self.ai_output.clear()
        self.ai_input.clear()

    def _build_internal_chat_tab(self) -> None:
        self.internal_chat_tab = InternalChatTab(self.client)
        self.tabs.addTab(self.internal_chat_tab, "Chat interna")

    def _build_analytics_tab(self) -> None:
        self.tabs.addTab(AnalyticsTab(self.client), "Analytics")

    def _build_whatsapp_tab(self) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form_row = QHBoxLayout()
        self.wa_phone = QLineEdit()
        self.wa_phone.setPlaceholderText("Telefono cliente (opz.)")
        self.wa_code = QLineEdit()
        self.wa_code.setPlaceholderText("Codice cliente (opz.)")
        form_row.addWidget(self.wa_phone)
        form_row.addWidget(self.wa_code)
        layout.addLayout(form_row)

        self.wa_inbound = QTextEdit()
        self.wa_inbound.setPlaceholderText("Incolla il messaggio ricevuto su WhatsApp...")
        self.wa_inbound.setMaximumHeight(120)
        layout.addWidget(self.wa_inbound)

        self.wa_send_api = QCheckBox("Invia via WhatsApp Business API (se configurata)")
        layout.addWidget(self.wa_send_api)

        gen_btn = QPushButton(f"Genera bozza con {AI_ASSISTANT_NAME}")
        copy_btn = QPushButton("Copia bozza")
        row = QHBoxLayout()
        row.addWidget(gen_btn)
        row.addWidget(copy_btn)
        layout.addLayout(row)

        self.wa_draft = QTextEdit()
        self.wa_draft.setReadOnly(True)
        layout.addWidget(self.wa_draft)

        def generate() -> None:
            msg = self.wa_inbound.toPlainText().strip()
            if not msg:
                return
            try:
                data = self.client.whatsapp_draft(
                    msg,
                    customer_phone=self.wa_phone.text().strip() or None,
                    customer_code=self.wa_code.text().strip() or None,
                    send_via_api=self.wa_send_api.isChecked(),
                )
                text = data.get("draft_reply", "")
                if data.get("sent"):
                    text += "\n\n✓ Inviato via WhatsApp API"
                elif data.get("send_status"):
                    text += f"\n\n⚠ {data.get('send_status')}"
                self.wa_draft.setPlainText(text)
            except Exception as exc:
                QMessageBox.warning(self, "Errore", str(exc))

        def copy() -> None:
            QApplication.clipboard().setText(self.wa_draft.toPlainText())

        gen_btn.clicked.connect(generate)
        copy_btn.clicked.connect(copy)
        self.tabs.addTab(widget, "WhatsApp")

    def _build_mail_tab(self) -> None:
        self.tabs.addTab(MailTab(self.client), "Posta")

    def _build_calendar_tab(self) -> None:
        self.calendar_tab = CalendarTab(self.client)
        self.tabs.addTab(self.calendar_tab, "Calendario")

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if hasattr(self, "calendar_tab") and widget is self.calendar_tab:
            self.calendar_tab.on_tab_activated()
        if hasattr(self, "internal_chat_tab") and widget is self.internal_chat_tab:
            self.internal_chat_tab.on_tab_activated()
        elif hasattr(self, "internal_chat_tab"):
            self.internal_chat_tab.on_tab_deactivated()

    def _build_macsystem_software_tab(self) -> None:
        self.tabs.addTab(MacSystemSoftwareTab(), "Altri software MacSystem")

    def _build_quote_tab(self) -> None:
        self.tabs.addTab(QuoteTab(self.client), "Preventivi")

    def _sync_easyone(self) -> None:
        self.sync_btn.setEnabled(False)
        self.statusBar().showMessage("Sincronizzazione EasyOne in corso...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            data = self.client.sync_orders()
            products_new = data.get("products_imported", 0)
            products_upd = data.get("products_updated", 0)
            stock = data.get("stock_updated", 0)
            customers_new = data.get("customers_imported", 0)
            customers_upd = data.get("customers_updated", 0)
            customers_total = data.get("customers_in_archive", 0)
            orders = data.get("orders_imported", 0)
            lines = data.get("lines_imported", 0)
            errors = data.get("errors", [])
            message = (
                f"Articoli nuovi: {products_new}\n"
                f"Articoli aggiornati: {products_upd}\n"
                f"Giacenze aggiornate: {stock}\n"
                f"Clienti nuovi: {customers_new}\n"
                f"Clienti aggiornati: {customers_upd}\n"
                f"Clienti in archivio: {customers_total}\n"
                f"Ordini importati: {orders}\n"
                f"Righe ordine: {lines}"
            )
            if errors:
                message += (
                    f"\n\nAvvisi ({len(errors)}):\n"
                    + "\n".join(errors[:5])
                )
                if len(errors) > 5:
                    message += f"\n... e altri {len(errors) - 5}"
            QMessageBox.information(self, "Sincronizzazione EasyOne", message)
            if hasattr(self, "customers_tab"):
                self.customers_tab.refresh_after_sync()
            synced_at = data.get("synced_at", "")
            if synced_at:
                self.statusBar().showMessage(f"Ultima sync EasyOne: {synced_at}")
            else:
                self.statusBar().showMessage(
                    f"Sync EasyOne completata — {orders} ordini importati"
                )
        except Exception as exc:
            QMessageBox.warning(self, "Sincronizzazione fallita", str(exc))
            self.statusBar().showMessage(self._status_user)
        finally:
            QApplication.restoreOverrideCursor()
            self.sync_btn.setEnabled(True)

    def _show_about(self) -> None:
        AboutDialog(self.client, self.config, self).exec()

    def closeEvent(self, event) -> None:
        self.client.logout()
        super().closeEvent(event)
