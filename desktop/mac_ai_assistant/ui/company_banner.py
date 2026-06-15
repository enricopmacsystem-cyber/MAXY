from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QWidget

from mac_ai_assistant.branding import (
    company_banner_path,
    header_logo_path,
    login_footer_logo_path,
)


def company_banner_label(
    parent: QWidget | None = None,
    *,
    max_height: int = 48,
    max_width: int | None = None,
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
) -> QLabel:
    """Etichetta con il banner aziendale Mac System, scalato in modo proporzionale."""
    label = QLabel(parent)
    label.setAlignment(alignment)
    label.setStyleSheet(
        "background-color: #ffffff; padding: 6px 12px; border-radius: 4px;"
    )

    path = company_banner_path()
    if not path:
        return label

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return label

    if max_width:
        scaled = pixmap.scaled(
            max_width,
            max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    else:
        scaled = pixmap.scaledToHeight(
            max_height,
            Qt.TransformationMode.SmoothTransformation,
        )

    label.setPixmap(scaled)
    return label


def header_logo_label(
    parent: QWidget | None = None,
    *,
    max_size: int = 48,
) -> QLabel:
    """Logo M Mac System in alto a sinistra (nitido, senza banda vuota)."""
    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet("background: transparent; padding: 0; margin: 0;")
    label.setFixedHeight(max_size + 4)

    path = header_logo_path()
    if not path:
        return label

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return label

    scaled = pixmap.scaled(
        max_size,
        max_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    label.setPixmap(scaled)
    label.setFixedWidth(scaled.width())
    return label


def login_footer_logo_label(
    parent: QWidget | None = None,
    *,
    max_width: int = 400,
    max_height: int = 72,
) -> QLabel:
    """Logo Mac System in basso alla schermata di login (senza banda bianca)."""
    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
    label.setStyleSheet("background: transparent; padding: 12px 0 4px 0;")

    path = login_footer_logo_path()
    if not path:
        return label

    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return label

    scaled = pixmap.scaled(
        max_width,
        max_height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    label.setPixmap(scaled)
    return label
