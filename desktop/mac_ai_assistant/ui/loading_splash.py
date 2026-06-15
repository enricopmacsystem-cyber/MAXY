from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from mac_ai_assistant.branding import splash_screen_path, window_title


class _CircularLoader(QWidget):
    """Indicatore di caricamento circolare animato."""

    def __init__(self, size: int = 52, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def stop(self) -> None:
        self._timer.stop()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 4
        rect = self.rect().adjusted(margin, margin, -margin, -margin)

        track = QPen(QColor("#e0e8f0"), 4)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawEllipse(rect)

        arc = QPen(QColor("#4a90d9"), 4)
        arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        span = 70 * 16
        start = -self._angle * 16
        painter.drawArc(rect, start, span)


class LoadingSplash(QWidget):
    """Splash post-login: logo Maxy nitido e loading circolare."""

    def __init__(self, message: str = "Caricamento in corso...", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background: #ffffff; border: 1px solid #d8e4f0; border-radius: 12px;")
        self.setFixedSize(400, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 32, 28, 28)
        layout.setSpacing(16)

        title = QLabel(window_title())
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1a3a5c; border: none;")
        layout.addWidget(title)

        self._logo = QLabel()
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setStyleSheet("border: none; background: transparent;")
        self._logo.setMinimumHeight(300)
        layout.addWidget(self._logo, stretch=1)

        self._loader = _CircularLoader(56)
        loader_row = QVBoxLayout()
        loader_row.addWidget(self._loader, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(loader_row)

        self._message = QLabel(message)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet("color: #555; border: none;")
        layout.addWidget(self._message)

        self._load_logo()

    def _load_logo(self) -> None:
        path = splash_screen_path()
        if not path:
            self._logo.setText("Maxy AI")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._logo.setText("Maxy AI")
            return
        scaled = pixmap.scaled(
            320,
            320,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._logo.setPixmap(scaled)

    def show_centered(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()

    def set_message(self, text: str) -> None:
        self._message.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event) -> None:
        self._loader.stop()
        super().closeEvent(event)

    def finish(self) -> None:
        self._loader.stop()
        self.close()
        QApplication.processEvents()
