"""Temi applicazione Maxy AI — sistema, chiaro, scuro, Classic, BigMac."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

APP_FONT_POINT_SIZE = 12
TEXT_AREA_FONT_POINT_SIZE = 14


class ThemeId(StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    CLASSIC = "classic"
    BIGMAC = "bigmac"


THEME_LABELS: dict[ThemeId, str] = {
    ThemeId.SYSTEM: "Predefinito di sistema",
    ThemeId.LIGHT: "Chiaro",
    ThemeId.DARK: "Scuro",
    ThemeId.CLASSIC: "Classic — Mac System",
    ThemeId.BIGMAC: "BigMac 🍔",
}


@dataclass(frozen=True)
class ThemeTokens:
    id: ThemeId
    window_bg: str
    surface: str
    surface_alt: str
    text: str
    text_muted: str
    primary: str
    primary_hover: str
    accent: str
    accent_hover: str
    border: str
    input_bg: str
    input_border: str
    table_bg: str
    table_alt: str
    header_bg: str
    tab_bg: str
    tab_text: str
    tab_hover_bg: str
    tab_hover_border: str
    tab_selected_bg: str
    tab_selected_accent: str
    toolbar_bg: str
    status_bg: str
    menu_bg: str
    chat_mine_bg: str
    chat_other_bg: str
    hint: str
    # BigMac / decorazioni opzionali
    top_strip: str | None = None
    subtitle: str | None = None


def _tokens_light() -> ThemeTokens:
    return ThemeTokens(
        id=ThemeId.LIGHT,
        window_bg="#f5f5f5",
        surface="#ffffff",
        surface_alt="#fafafa",
        text="#1a1a1a",
        text_muted="#555555",
        primary="#0078d4",
        primary_hover="#106ebe",
        accent="#00a86b",
        accent_hover="#008f5a",
        border="#d0d0d0",
        input_bg="#ffffff",
        input_border="#bdbdbd",
        table_bg="#ffffff",
        table_alt="#f7f7f7",
        header_bg="#ececec",
        tab_bg="#e8e8e8",
        tab_text="#333333",
        tab_hover_bg="#ddebf7",
        tab_hover_border="#0078d4",
        tab_selected_bg="#0078d4",
        tab_selected_accent="#00a86b",
        toolbar_bg="#ffffff",
        status_bg="#003b7a",
        menu_bg="#ffffff",
        chat_mine_bg="#0078d4",
        chat_other_bg="#e8e8e8",
        hint="#555555",
    )


def _tokens_dark() -> ThemeTokens:
    return ThemeTokens(
        id=ThemeId.DARK,
        window_bg="#1e1e1e",
        surface="#252526",
        surface_alt="#2d2d30",
        text="#e8e8e8",
        text_muted="#b0b0b0",
        primary="#0078d4",
        primary_hover="#1084d8",
        accent="#00c853",
        accent_hover="#00a846",
        border="#3e3e42",
        input_bg="#2d2d30",
        input_border="#555555",
        table_bg="#252526",
        table_alt="#2a2a2d",
        header_bg="#333337",
        tab_bg="#2d2d30",
        tab_text="#b0b0b0",
        tab_hover_bg="#3a3f47",
        tab_hover_border="#4a90d9",
        tab_selected_bg="#0078d4",
        tab_selected_accent="#00c853",
        toolbar_bg="#252526",
        status_bg="#007acc",
        menu_bg="#252526",
        chat_mine_bg="#0078d4",
        chat_other_bg="#2d2d30",
        hint="#aaaaaa",
    )


def _tokens_classic() -> ThemeTokens:
    """Bianco, blu e grigi — identità Mac System Gruaro."""
    return ThemeTokens(
        id=ThemeId.CLASSIC,
        window_bg="#eef2f7",
        surface="#ffffff",
        surface_alt="#f4f7fb",
        text="#1a2a3a",
        text_muted="#4a5f73",
        primary="#003b7a",
        primary_hover="#002d5c",
        accent="#0078d4",
        accent_hover="#005fa3",
        border="#c5d0dc",
        input_bg="#ffffff",
        input_border="#a8b8c8",
        table_bg="#ffffff",
        table_alt="#f0f4f9",
        header_bg="#dce6f2",
        tab_bg="#e8eef5",
        tab_text="#1a3a5c",
        tab_hover_bg="#d4e4f5",
        tab_hover_border="#0078d4",
        tab_selected_bg="#003b7a",
        tab_selected_accent="#0078d4",
        toolbar_bg="#ffffff",
        status_bg="#003b7a",
        menu_bg="#ffffff",
        chat_mine_bg="#003b7a",
        chat_other_bg="#e8eef5",
        hint="#4a5f73",
        subtitle="MacSystem s.r.l. — Classic",
    )


def _tokens_bigmac() -> ThemeTokens:
    """Pane dorato, sesamo, lattuga, ketchup e formaggio."""
    return ThemeTokens(
        id=ThemeId.BIGMAC,
        window_bg="#f5c842",
        surface="#fff8e7",
        surface_alt="#ffefb8",
        text="#3d2314",
        text_muted="#6b4423",
        primary="#c41e3a",
        primary_hover="#a01830",
        accent="#2e7d32",
        accent_hover="#256628",
        border="#8b5a2b",
        input_bg="#fffdf5",
        input_border="#c9a227",
        table_bg="#fff8e7",
        table_alt="#ffefb8",
        header_bg="#e8b84a",
        tab_bg="#e8a317",
        tab_text="#3d2314",
        tab_hover_bg="#ffc72c",
        tab_hover_border="#2e7d32",
        tab_selected_bg="#c41e3a",
        tab_selected_accent="#2e7d32",
        toolbar_bg="#e8a317",
        status_bg="#6b3e26",
        menu_bg="#e8b84a",
        chat_mine_bg="#c41e3a",
        chat_other_bg="#ffefb8",
        hint="#6b4423",
        top_strip="#d4a017",
        subtitle="Due all-beef patties, special sauce…",
    )


_THEME_BUILDERS = {
    ThemeId.LIGHT: _tokens_light,
    ThemeId.DARK: _tokens_dark,
    ThemeId.CLASSIC: _tokens_classic,
    ThemeId.BIGMAC: _tokens_bigmac,
}


def detect_system_dark() -> bool:
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except Exception:
        return False


def resolve_theme(theme_id: ThemeId | str) -> ThemeTokens:
    try:
        tid = ThemeId(str(theme_id))
    except ValueError:
        tid = ThemeId.SYSTEM

    if tid == ThemeId.SYSTEM:
        return _tokens_dark() if detect_system_dark() else _tokens_light()

    builder = _THEME_BUILDERS.get(tid, _tokens_light)
    return builder()


def build_app_stylesheet(tokens: ThemeTokens) -> str:
    t = tokens
    top_bar = ""
    if t.top_strip:
        top_bar = f"""
QMainWindow::separator {{
    background: {t.top_strip};
    height: 4px;
}}
"""

    bigmac_banner = ""
    if t.id == ThemeId.BIGMAC:
        bigmac_banner = f"""
QMainWindow {{
    border-top: 6px solid {t.top_strip or t.toolbar_bg};
}}
QWidget#centralRoot {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {t.toolbar_bg}, stop:0.08 {t.window_bg}, stop:1 {t.surface});
}}
"""

    return f"""
/* Maxy AI — tema {t.id} */
QWidget {{
    background-color: {t.window_bg};
    color: {t.text};
    font-family: "Segoe UI", sans-serif;
    font-size: {APP_FONT_POINT_SIZE}pt;
}}
QMainWindow, QDialog {{
    background-color: {t.window_bg};
    color: {t.text};
}}
{top_bar}
{bigmac_banner}
QLabel {{
    color: {t.text};
    background: transparent;
}}
QLabel[hint="true"] {{
    color: {t.hint};
}}
QPushButton {{
    background-color: {t.surface_alt};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 5px;
    padding: 6px 14px;
    min-height: 22px;
}}
QPushButton:hover {{
    background-color: {t.tab_hover_bg};
    border-color: {t.primary};
}}
QPushButton:pressed {{
    background-color: {t.primary};
    color: #ffffff;
}}
QPushButton#primaryBtn {{
    background-color: {t.primary};
    color: #ffffff;
    border: 1px solid {t.primary_hover};
    font-weight: bold;
}}
QPushButton#primaryBtn:hover {{
    background-color: {t.primary_hover};
}}
QPushButton#aiModeBtn {{
    font-size: 13pt;
    font-weight: 600;
    padding: 12px 18px;
    min-height: 48px;
    border-radius: 8px;
    border: 2px solid {t.border};
}}
QPushButton#aiModeBtn:hover {{
    border-color: {t.primary};
    background-color: {t.tab_hover_bg};
}}
QPushButton#aiModeBtn:checked {{
    background-color: {t.primary};
    color: #ffffff;
    border: 2px solid {t.primary_hover};
}}
QPushButton#aiModeBtn:checked:hover {{
    background-color: {t.primary_hover};
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: {t.input_bg};
    color: {t.text};
    border: 1px solid {t.input_border};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: {TEXT_AREA_FONT_POINT_SIZE}pt;
    selection-background-color: {t.primary};
    selection-color: #ffffff;
}}
QTextEdit#aiOutput, QTextEdit#aiInput {{
    font-size: {TEXT_AREA_FONT_POINT_SIZE + 1}pt;
    line-height: 1.45;
}}
QTableWidget {{
    background-color: {t.table_bg};
    color: {t.text};
    gridline-color: {t.border};
    border: 1px solid {t.border};
    alternate-background-color: {t.table_alt};
}}
QHeaderView::section {{
    background-color: {t.header_bg};
    color: {t.text};
    padding: 6px;
    border: 1px solid {t.border};
    font-weight: bold;
}}
QTabWidget::pane {{
    border: 1px solid {t.border};
    border-top: none;
    background: {t.surface};
}}
QTabBar::tab {{
    background: {t.tab_bg};
    color: {t.tab_text};
    border: 1px solid {t.border};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 3px;
    min-width: 72px;
}}
QTabBar::tab:hover {{
    background: {t.tab_hover_bg};
    color: {t.text};
    border: 1px solid {t.tab_hover_border};
    border-bottom: 2px solid {t.tab_hover_border};
}}
QTabBar::tab:selected {{
    background: {t.tab_selected_bg};
    color: #ffffff;
    font-weight: bold;
    border: 1px solid {t.tab_selected_bg};
    border-bottom: 3px solid {t.tab_selected_accent};
}}
QMenuBar {{
    background-color: {t.menu_bg};
    color: {t.text};
    border-bottom: 1px solid {t.border};
}}
QMenuBar::item:selected {{
    background: {t.tab_hover_bg};
}}
QMenu {{
    background-color: {t.surface};
    color: {t.text};
    border: 1px solid {t.border};
}}
QMenu::item:selected {{
    background-color: {t.primary};
    color: #ffffff;
}}
QStatusBar {{
    background-color: {t.status_bg};
    color: #ffffff;
}}
QCheckBox {{
    color: {t.text};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border};
    border-radius: 3px;
    background: {t.input_bg};
}}
QCheckBox::indicator:checked {{
    background: {t.primary};
    border-color: {t.primary};
}}
QScrollBar:vertical {{
    background: {t.surface_alt};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border};
    border-radius: 4px;
    min-height: 24px;
}}
QSplitter::handle {{
    background: {t.border};
}}
"""


def build_dialog_stylesheet(tokens: ThemeTokens) -> str:
    t = tokens
    return f"""
QDialog {{
    background-color: {t.surface};
    color: {t.text};
}}
QWidget {{
    background-color: {t.surface};
    color: {t.text};
}}
QLabel {{
    color: {t.text};
    background: transparent;
}}
QPushButton {{
    color: {t.text};
    background-color: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: 4px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    background-color: {t.tab_hover_bg};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {t.input_bg};
    color: {t.text};
    border: 1px solid {t.input_border};
}}
"""


_current_theme_id: ThemeId = ThemeId.SYSTEM
_current_tokens: ThemeTokens = _tokens_light()


def current_theme_id() -> ThemeId:
    return _current_theme_id


def current_tokens() -> ThemeTokens:
    return _current_tokens


def apply_theme(app: QApplication, theme_id: ThemeId | str) -> ThemeTokens:
    global _current_theme_id, _current_tokens
    try:
        _current_theme_id = ThemeId(str(theme_id))
    except ValueError:
        _current_theme_id = ThemeId.SYSTEM

    tokens = resolve_theme(_current_theme_id)
    _current_tokens = tokens

    base_font = QFont("Segoe UI", APP_FONT_POINT_SIZE)
    app.setFont(base_font)
    app.setStyleSheet(build_app_stylesheet(tokens))

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens.window_bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens.input_bg))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens.surface_alt))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens.surface_alt))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens.text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens.primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    return tokens
