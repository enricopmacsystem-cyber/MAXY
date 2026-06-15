from __future__ import annotations

import sys
import traceback
from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.branding import (
    APP_DISPLAY_NAME,
    ORGANIZATION_NAME,
    app_icon_path,
    splash_screen_path,
)
from mac_ai_assistant.config import AppConfig, get_logs_dir
from mac_ai_assistant.hub_launcher import ensure_hub_running
from mac_ai_assistant.ui.loading_splash import LoadingSplash
from mac_ai_assistant.ui.login_dialog import LoginDialog
from mac_ai_assistant.ui.main_window import MainWindow
from mac_ai_assistant.ui.theme_preferences import apply_saved_theme


def _prepare_qt_app() -> None:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def _init_web_engine() -> None:
    try:
        from PySide6.QtWebEngineCore import QtWebEngine

        QtWebEngine.initialize()
    except Exception:
        pass


def _log_crash(exc: BaseException) -> None:
    try:
        log_file = get_logs_dir() / f"crash_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.log"
        log_file.write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass


def _splash_screen(app: QApplication) -> QSplashScreen:
    splash_path = splash_screen_path()
    if splash_path:
        pixmap = QPixmap(str(splash_path))
        if not pixmap.isNull():
            splash = QSplashScreen(pixmap)
            splash.showMessage(
                "Avvio in corso...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor("#666666"),
            )
            return splash

    icon = app_icon_path()
    if icon:
        pixmap = QPixmap(str(icon))
        if not pixmap.isNull():
            canvas = QPixmap(320, 320)
            canvas.fill(Qt.GlobalColor.white)
            scaled = pixmap.scaled(
                200,
                200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter = QPainter(canvas)
            painter.fillRect(canvas.rect(), Qt.GlobalColor.white)
            x = (canvas.width() - scaled.width()) // 2
            y = (canvas.height() - scaled.height()) // 2 - 10
            painter.drawPixmap(x, y, scaled)
            painter.end()
            splash = QSplashScreen(canvas)
            splash.showMessage(
                "Avvio in corso...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                QColor("#666666"),
            )
            return splash

    fallback = QPixmap(400, 280)
    fallback.fill(Qt.GlobalColor.white)
    splash = QSplashScreen(fallback)
    splash.showMessage(
        "Avvio Maxy AI...",
        Qt.AlignmentFlag.AlignCenter,
        QColor("#333333"),
    )
    return splash


def main() -> int:
    _prepare_qt_app()
    config = AppConfig.load()
    app = QApplication(sys.argv)
    _init_web_engine()
    apply_saved_theme(app)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationVersion(config.app_version)
    app.setOrganizationName(ORGANIZATION_NAME)

    icon = app_icon_path()
    if icon:
        app.setWindowIcon(QIcon(str(icon)))

    splash = _splash_screen(app)
    splash.show()
    app.processEvents()

    hub_ok, hub_error = ensure_hub_running(config.hub_base_url)
    splash.finish(None)

    if not hub_ok:
        QMessageBox.critical(None, APP_DISPLAY_NAME, hub_error)
        return 1

    client = HubClient(config.hub_base_url)

    if not client.is_authenticated:
        client.try_restore_session()

    if not client.is_authenticated:
        dialog = LoginDialog(client)
        if dialog.exec() != LoginDialog.DialogCode.Accepted:
            return 0

    loading = LoadingSplash("Preparazione dell'interfaccia...")
    loading.show_centered()

    try:
        loading.set_message("Caricamento moduli...")
        window = MainWindow(client, config)
        loading.set_message("Avvio completato")
        loading.finish()
        window.show()
        app.processEvents()
        return app.exec()
    except Exception as exc:
        loading.finish()
        _log_crash(exc)
        QMessageBox.critical(
            None,
            "Errore applicazione",
            f"{exc}\n\nDettagli salvati in:\n{get_logs_dir()}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
