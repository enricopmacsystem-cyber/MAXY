"""Scheda download altri software MacSystem."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from mac_ai_assistant.branding import (
    ANDROID_APK_NAME,
    ANDROID_DESKTOP_FILENAME,
    CONNECT_DESKTOP_FILENAME,
    CONNECT_EXE_NAME,
    MACSYSTEM_HOMEPAGE_URL,
    bundled_software_path,
)

_HOVER_ACTION_BUTTON = """
QPushButton {{
    background-color: {base};
    color: {text};
    border: 2px solid {border};
    border-radius: 10px;
    padding: 14px 22px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {hover_bg};
    border: 2px solid {hover_border};
    color: {hover_text};
    padding: 16px 24px;
    font-weight: 700;
}}
QPushButton:pressed {{
    background-color: {pressed};
}}
"""

_ANDROID_BANNER_STYLE = """
QPushButton#androidNovitaBanner {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #1b5e20, stop:0.5 #2e7d32, stop:1 #43a047
    );
    color: #ffffff;
    border: 2px solid #81c784;
    border-radius: 12px;
    padding: 18px 24px;
    font-size: 16px;
    font-weight: 700;
    text-align: left;
}}
QPushButton#androidNovitaBanner:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #2e7d32, stop:0.5 #43a047, stop:1 #66bb6a
    );
    border: 3px solid #b9f6ca;
    color: #ffffff;
    padding: 20px 26px;
    font-size: 17px;
}}
QPushButton#androidNovitaBanner:pressed {{
    background-color: #1b5e20;
}}
"""

_HOMEPAGE_LINK_STYLE = """
QPushButton#macsystemHomepageLink {{
    background: transparent;
    color: #0078d4;
    border: none;
    font-size: 14px;
    font-weight: 600;
    text-align: left;
    padding: 4px 0;
}}
QPushButton#macsystemHomepageLink:hover {{
    color: #005a9e;
    text-decoration: underline;
    font-size: 15px;
    font-weight: 700;
}}
"""


def _user_desktop_dir() -> Path:
    profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    for name in ("Desktop", "Scrivania"):
        candidate = profile / name
        if candidate.is_dir():
            return candidate
    return profile / "Desktop"


def _hover_button(
    label: str,
    *,
    base: str = "#0078d4",
    hover_bg: str = "#106ebe",
    border: str = "#005a9e",
    hover_border: str = "#00c853",
    text: str = "#ffffff",
    hover_text: str = "#ffffff",
    pressed: str = "#004578",
) -> QPushButton:
    button = QPushButton(label)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(
        _HOVER_ACTION_BUTTON.format(
            base=base,
            hover_bg=hover_bg,
            border=border,
            hover_border=hover_border,
            text=text,
            hover_text=hover_text,
            pressed=pressed,
        )
    )
    return button


def _copy_bundled_to_desktop(source: Path, desktop_name: str) -> Path:
    destination = _user_desktop_dir() / desktop_name
    shutil.copy2(source, destination)
    return destination


class MacSystemSoftwareTab(QWidget):
    """Altri software MacSystem: Connect, app Android, link al sito."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("macsystemSoftwareTab")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 24)
        layout.setSpacing(18)

        title = QLabel("Altri software MacSystem")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a3a5c;")
        layout.addWidget(title)

        intro = QLabel(
            "Scarica gli strumenti MacSystem direttamente dall'app. "
            f"Il banner Android salva {ANDROID_DESKTOP_FILENAME} sul Desktop con un clic. "
            "Passa il mouse sui pulsanti per evidenziarli."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #333; font-size: 13px;")
        layout.addWidget(intro)

        layout.addWidget(self._build_connect_card())
        layout.addWidget(self._build_android_banner())
        layout.addWidget(self._build_follow_section())
        layout.addStretch()

    def _card_frame(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("softwareCard")
        frame.setStyleSheet(
            "QFrame#softwareCard {"
            "  background: #f8fbff;"
            "  border: 1px solid #c5d9eb;"
            "  border-radius: 12px;"
            "}"
        )
        return frame

    def _build_connect_card(self) -> QFrame:
        card = self._card_frame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        heading = QLabel("MacSystem Connect")
        heading.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a3a5c;")
        card_layout.addWidget(heading)

        description = QLabel(
            "Assistenza remota MacSystem: consente ai tecnici di collegarsi al tuo PC "
            "in modo sicuro per supporto e manutenzione."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #444; font-size: 13px;")
        card_layout.addWidget(description)

        download_btn = _hover_button(
            "Salva MacSystem Connect sul Desktop",
            base="#0078d4",
            hover_bg="#1a8cff",
            hover_border="#00e676",
        )
        download_btn.clicked.connect(self._save_connect_to_desktop)
        card_layout.addWidget(download_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        return card

    def _build_android_banner(self) -> QPushButton:
        banner = QPushButton("NOVITÀ: disponibile per Android: MacSystem App")
        banner.setObjectName("androidNovitaBanner")
        banner.setCursor(Qt.CursorShape.PointingHandCursor)
        banner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        banner.setStyleSheet(_ANDROID_BANNER_STYLE)
        banner.setToolTip(
            f"Scarica subito {ANDROID_DESKTOP_FILENAME} e salvalo sul Desktop del PC"
        )
        banner.clicked.connect(self._save_android_apk_to_desktop)
        return banner

    def _build_follow_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #fff8e1; border: 1px solid #ffe082; border-radius: 10px; }"
        )
        section = QVBoxLayout(frame)
        section.setContentsMargins(16, 14, 16, 14)
        section.setSpacing(8)

        follow = QLabel("Seguici per tutte le novità e visita")
        follow.setStyleSheet("font-size: 14px; font-weight: 600; color: #5d4037;")
        section.addWidget(follow)

        link = QPushButton(MACSYSTEM_HOMEPAGE_URL)
        link.setObjectName("macsystemHomepageLink")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.setStyleSheet(_HOMEPAGE_LINK_STYLE)
        link.setToolTip("Apri il sito MacSystem nel browser")
        link.clicked.connect(self._open_homepage)
        section.addWidget(link, alignment=Qt.AlignmentFlag.AlignLeft)
        return frame

    def _save_connect_to_desktop(self) -> None:
        source = bundled_software_path(CONNECT_EXE_NAME)
        if source is None:
            QMessageBox.warning(
                self,
                "MacSystem Connect",
                "Il file di installazione non è disponibile in questo pacchetto.\n"
                "Contatta l'assistenza MacSystem o visita il sito ufficiale.",
            )
            return
        try:
            destination = _copy_bundled_to_desktop(source, CONNECT_DESKTOP_FILENAME)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "MacSystem Connect",
                f"Impossibile salvare sul Desktop:\n{exc}",
            )
            return
        QMessageBox.information(
            self,
            "MacSystem Connect",
            f"Assistenza remota salvata sul Desktop:\n{destination}",
        )

    def _save_android_apk_to_desktop(self) -> None:
        source = bundled_software_path(ANDROID_APK_NAME)
        if source is None:
            QMessageBox.warning(
                self,
                "MacSystem App",
                f"{ANDROID_APK_NAME} non è disponibile in questo pacchetto.\n"
                "Contatta l'assistenza MacSystem o visita il sito ufficiale.",
            )
            return
        try:
            destination = _copy_bundled_to_desktop(source, ANDROID_DESKTOP_FILENAME)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "MacSystem App",
                f"Impossibile salvare {ANDROID_DESKTOP_FILENAME} sul PC:\n{exc}",
            )
            return
        QMessageBox.information(
            self,
            "MacSystem App — download completato",
            f"Scaricato e salvato sul Desktop:\n{destination}\n\n"
            "Trasferisci il file sul telefono Android e aprilo per installare l'app.",
        )

    def _open_homepage(self) -> None:
        QDesktopServices.openUrl(QUrl(MACSYSTEM_HOMEPAGE_URL))
