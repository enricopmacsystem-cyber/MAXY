"""Persistenza e applicazione preferenze tema."""

from __future__ import annotations

from configparser import ConfigParser

from PySide6.QtWidgets import QApplication, QWidget

from mac_ai_assistant.config import get_config_path
from mac_ai_assistant.ui.themes import (
    THEME_LABELS,
    ThemeId,
    apply_theme,
    build_dialog_stylesheet,
    current_tokens,
)


def load_theme_id() -> ThemeId:
    path = get_config_path()
    if not path.is_file():
        return ThemeId.SYSTEM

    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    if not parser.has_option("ui", "theme"):
        return ThemeId.SYSTEM

    raw = parser.get("ui", "theme", fallback="system").strip().lower()
    try:
        return ThemeId(raw)
    except ValueError:
        return ThemeId.SYSTEM


def save_theme_id(theme_id: ThemeId) -> None:
    path = get_config_path()
    parser = ConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    if not parser.has_section("ui"):
        parser.add_section("ui")
    parser.set("ui", "theme", theme_id.value)
    with path.open("w", encoding="utf-8") as fh:
        parser.write(fh)


def apply_saved_theme(app: QApplication) -> None:
    apply_theme(app, load_theme_id())


def set_theme(app: QApplication, theme_id: ThemeId) -> None:
    save_theme_id(theme_id)
    apply_theme(app, theme_id)


def dialog_style() -> str:
    return build_dialog_stylesheet(current_tokens())


def style_hint_label() -> str:
    return f"color: {current_tokens().hint};"


def style_muted_label() -> str:
    return f"color: {current_tokens().text_muted};"


def style_primary_button() -> str:
    t = current_tokens()
    return (
        f"QPushButton {{ background: {t.primary}; color: #fff; font-weight: bold;"
        f" padding: 6px 14px; border-radius: 4px; border: none; }}"
        f"QPushButton:hover {{ background: {t.primary_hover}; }}"
    )


def refresh_widget_tree(root: QWidget | None) -> None:
    """Forza aggiornamento visivo dopo cambio tema."""
    if root is None:
        return
    root.setStyleSheet("")
    root.update()
    for child in root.findChildren(QWidget):
        child.style().unpolish(child)
        child.style().polish(child)
        child.update()
