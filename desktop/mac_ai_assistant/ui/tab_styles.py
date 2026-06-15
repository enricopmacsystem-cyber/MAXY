"""Stili condivisi per le schede principali."""

MAIN_TAB_WIDGET_STYLE = """
QTabWidget::pane {
    border: 1px solid #3e3e42;
    border-top: none;
    background: #1e1e1e;
}
QTabBar::tab {
    background: #2d2d30;
    color: #b0b0b0;
    border: 1px solid #3e3e42;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 3px;
    min-width: 72px;
}
QTabBar::tab:hover {
    background: #3a3f47;
    color: #ffffff;
    border: 1px solid #4a90d9;
    border-bottom: 2px solid #4a90d9;
}
QTabBar::tab:selected {
    background: #0078d4;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #0078d4;
    border-bottom: 2px solid #00c853;
}
QTabBar::tab:selected:hover {
    background: #1084d8;
    color: #ffffff;
}
"""
