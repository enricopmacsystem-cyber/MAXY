from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.api.hub_client import HubClient
from mac_ai_assistant.branding import (
    APP_VERSION_LABEL,
    BUILD_NAME,
    DEVELOPER_EMAIL,
    DEVELOPER_NAME,
    ORGANIZATION_NAME,
    splash_screen_path,
    window_title,
)
from mac_ai_assistant.config import AppConfig
from mac_ai_assistant.ui.release_info_dialog import ReleaseInfoDialog
from mac_ai_assistant.ui.theme_preferences import dialog_style, style_muted_label


class _ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _DaisyPluckWidget(QWidget):
    """Margherita interattiva: strappa i petali fino al sorriso finale."""

    finished = Signal()

    _PETAL_COUNT = 12
    _CENTER_RADIUS = 28
    _PETAL_LENGTH = 52
    _PETAL_WIDTH = 22

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._removed: set[int] = set()
        self._show_smile = False
        self.setMinimumSize(360, 360)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def reset(self) -> None:
        self._removed.clear()
        self._show_smile = False
        self.update()

    def _center(self) -> tuple[float, float]:
        return self.width() / 2, self.height() / 2

    def _petal_polygon(self, index: int) -> list[tuple[float, float]]:
        cx, cy = self._center()
        angle = math.radians(index * (360 / self._PETAL_COUNT) - 90)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        px = -sin_a
        py = cos_a
        tip_x = cx + cos_a * (self._CENTER_RADIUS + self._PETAL_LENGTH)
        tip_y = cy + sin_a * (self._CENTER_RADIUS + self._PETAL_LENGTH)
        base_x = cx + cos_a * self._CENTER_RADIUS
        base_y = cy + sin_a * self._CENTER_RADIUS
        half_w = self._PETAL_WIDTH / 2
        return [
            (base_x + px * half_w, base_y + py * half_w),
            (tip_x, tip_y),
            (base_x - px * half_w, base_y - py * half_w),
        ]

    def _petal_at(self, pos) -> int | None:
        for index in range(self._PETAL_COUNT):
            if index in self._removed:
                continue
            points = self._petal_polygon(index)
            min_x = min(p[0] for p in points) - 8
            max_x = max(p[0] for p in points) + 8
            min_y = min(p[1] for p in points) - 8
            max_y = max(p[1] for p in points) + 8
            if min_x <= pos.x() <= max_x and min_y <= pos.y() <= max_y:
                return index
        return None

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)

        cx, cy = self._center()
        petal_color = QColor("#FFF8E7")
        petal_edge = QColor("#F2D98B")
        painter.setPen(QPen(petal_edge, 1.2))
        painter.setBrush(petal_color)
        for index in range(self._PETAL_COUNT):
            if index in self._removed:
                continue
            points = self._petal_polygon(index)
            polygon = QPolygonF([QPointF(x, y) for x, y in points])
            painter.drawPolygon(polygon)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFD54F"))
        painter.drawEllipse(
            int(cx - self._CENTER_RADIUS),
            int(cy - self._CENTER_RADIUS),
            self._CENTER_RADIUS * 2,
            self._CENTER_RADIUS * 2,
        )

        if self._show_smile:
            painter.setPen(QPen(QColor("#5D4037"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            eye_y = cy - 8
            painter.drawEllipse(int(cx - 18), int(eye_y - 6), 10, 14)
            painter.drawEllipse(int(cx + 8), int(eye_y - 6), 10, 14)
            painter.drawArc(int(cx - 22), int(cy - 2), 44, 30, 200 * 16, 140 * 16)

    def mousePressEvent(self, event) -> None:
        if self._show_smile:
            return
        petal = self._petal_at(event.position())
        if petal is None:
            return
        self._removed.add(petal)
        self.update()
        if len(self._removed) >= self._PETAL_COUNT:
            self._show_smile = True
            self.update()
            QTimer.singleShot(2200, self.finished.emit)


class AboutDialog(QDialog):
    def __init__(
        self,
        client: HubClient,
        config: AppConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.client = client
        self.config = config
        self.setWindowTitle("Informazioni")
        self.setMinimumWidth(420)
        self.setStyleSheet(dialog_style())
        self._build_clicks = 0
        self._build_click_timer = QTimer(self)
        self._build_click_timer.setSingleShot(True)
        self._build_click_timer.setInterval(900)
        self._build_click_timer.timeout.connect(self._on_build_click_timeout)

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        self._info_page = QWidget()
        info_layout = QVBoxLayout(self._info_page)
        info_layout.setSpacing(10)

        splash = splash_screen_path()
        if splash and splash.is_file():
            logo = QLabel()
            pixmap = QPixmap(str(splash))
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(
                        220,
                        220,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                info_layout.addWidget(logo)

        title = QLabel(window_title())
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #1a1a1a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(title)

        org = QLabel(ORGANIZATION_NAME)
        org.setAlignment(Qt.AlignmentFlag.AlignCenter)
        org.setStyleSheet(style_muted_label())
        info_layout.addWidget(org)

        info_layout.addWidget(self._info_row("Versione", APP_VERSION_LABEL))
        info_layout.addWidget(self._info_row("Sviluppatore", DEVELOPER_NAME))
        info_layout.addWidget(self._contact_row())

        build_row = QHBoxLayout()
        build_caption = QLabel("Build")
        build_caption.setStyleSheet("color: #555; min-width: 110px;")
        self.build_value = _ClickableLabel(BUILD_NAME)
        self.build_value.setStyleSheet(
            "color: #1a3a5c; font-weight: bold; text-decoration: underline;"
        )
        self.build_value.setCursor(Qt.CursorShape.PointingHandCursor)
        self.build_value.setToolTip("")
        self.build_value.clicked.connect(self._on_build_clicked)
        build_row.addWidget(build_caption)
        build_row.addWidget(self.build_value, stretch=1)
        info_layout.addLayout(build_row)

        info_layout.addSpacing(8)
        actions_row = QHBoxLayout()
        self.release_btn = QPushButton("Release info")
        self.release_btn.setToolTip(
            "Elenco funzioni, correzioni e implementazioni di questa versione"
        )
        self.release_btn.clicked.connect(self._show_release_info)
        self.update_btn = QPushButton("Verifica aggiornamenti")
        self.update_btn.clicked.connect(self._check_updates)
        actions_row.addWidget(self.release_btn)
        actions_row.addWidget(self.update_btn)
        info_layout.addLayout(actions_row)

        self.update_status = QLabel("")
        self.update_status.setWordWrap(True)
        self.update_status.setStyleSheet("color: #444; padding: 4px 0;")
        info_layout.addWidget(self.update_status)

        info_layout.addStretch()
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        info_layout.addWidget(close_btn)

        self._daisy_page = QWidget()
        daisy_layout = QVBoxLayout(self._daisy_page)
        daisy_hint = QLabel("Strappa i petali uno ad uno…")
        daisy_hint.setStyleSheet("color: #333;")
        daisy_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        daisy_layout.addWidget(daisy_hint)
        self.daisy_widget = _DaisyPluckWidget()
        daisy_layout.addWidget(self.daisy_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.daisy_widget.finished.connect(self._on_daisy_finished)

        self.stack.addWidget(self._info_page)
        self.stack.addWidget(self._daisy_page)

    def _contact_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel("Contatto")
        caption.setStyleSheet("color: #555; min-width: 110px;")
        email = QLabel(
            f'<a href="mailto:{DEVELOPER_EMAIL}" style="color: #0078D4; font-weight: bold;">'
            f"{DEVELOPER_EMAIL}</a>"
        )
        email.setTextFormat(Qt.TextFormat.RichText)
        email.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        email.setOpenExternalLinks(True)
        layout.addWidget(caption)
        layout.addWidget(email, stretch=1)
        return row

    def _info_row(self, label: str, value: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setStyleSheet("color: #555; min-width: 110px;")
        text = QLabel(value)
        text.setStyleSheet("font-weight: bold; color: #1a1a1a;")
        layout.addWidget(caption)
        layout.addWidget(text, stretch=1)
        return row

    def _on_build_clicked(self) -> None:
        self._build_clicks += 1
        if not self._build_click_timer.isActive():
            self._build_click_timer.start()
        if self._build_clicks >= 3:
            self._build_clicks = 0
            self._build_click_timer.stop()
            self._show_daisy()

    def _on_build_click_timeout(self) -> None:
        self._build_clicks = 0

    def _show_daisy(self) -> None:
        self.daisy_widget.reset()
        self.stack.setCurrentWidget(self._daisy_page)

    def _on_daisy_finished(self) -> None:
        self.stack.setCurrentWidget(self._info_page)

    def showEvent(self, event) -> None:
        self.setStyleSheet(dialog_style())
        super().showEvent(event)

    def _show_release_info(self) -> None:
        ReleaseInfoDialog(self).exec()

    def _check_updates(self) -> None:
        self.update_btn.setEnabled(False)
        self.update_status.setText("Verifica in corso…")
        try:
            data = self.client.check_updates(self.config.app_version)
            if data.get("update_available"):
                latest = data.get("latest_version", "?")
                notes = (data.get("release_notes") or "").strip()
                message = f"È disponibile una nuova versione: {latest}."
                if notes:
                    message += f"\n\n{notes}"
                self.update_status.setText(message)
            else:
                self.update_status.setText(
                    f"Stai usando l'ultima versione disponibile ({APP_VERSION_LABEL})."
                )
        except Exception as exc:
            self.update_status.setText(f"Verifica non riuscita: {exc}")
        finally:
            self.update_btn.setEnabled(True)
