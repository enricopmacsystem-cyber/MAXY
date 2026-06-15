"""Stili dialoghi con colori espliciti (compatibile tema scuro Windows)."""

LIGHT_DIALOG_STYLE = """
QDialog {
    background-color: #ffffff;
    color: #1a1a1a;
}
QWidget {
    background-color: #ffffff;
    color: #1a1a1a;
}
QLabel {
    color: #1a1a1a;
    background: transparent;
}
QPushButton {
    color: #1a1a1a;
    background-color: #f0f0f0;
    border: 1px solid #bdbdbd;
    border-radius: 4px;
    padding: 6px 14px;
    min-height: 24px;
}
QPushButton:hover {
    background-color: #e4e4e4;
    border-color: #9e9e9e;
}
QTextEdit, QPlainTextEdit {
    background-color: #fafafa;
    color: #1a1a1a;
    border: 1px solid #cfcfcf;
    selection-background-color: #cce8ff;
    selection-color: #000000;
}
"""
