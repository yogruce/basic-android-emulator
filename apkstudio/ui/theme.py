"""Koyu ve Açık tema stilleri."""

DARK_THEME = """
QMainWindow {
    background-color: #0D1117;
}
QWidget {
    color: #E6EDF3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QFrame#panelFrame {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
}
QFrame#viewportFrame {
    background-color: #010409;
    border: 1px solid #30363D;
    border-radius: 8px;
}
QFrame#screenSlot {
    background-color: #000000;
    border: 2px solid #00E5FF;
    border-radius: 6px;
}
QPushButton {
    background-color: #21262D;
    color: #E6EDF3;
    border: 1px solid #30363D;
    padding: 7px 14px;
    border-radius: 6px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363D;
    border-color: #8B949E;
}
QPushButton:pressed {
    background-color: #161B22;
}
QPushButton:disabled {
    background-color: #161B22;
    color: #484F58;
    border-color: #21262D;
}
QPushButton#primaryBtn {
    background-color: #00897B;
    border-color: #00897B;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #00796B;
}
QPushButton#accentBtn {
    background-color: #1F6FEB;
    border-color: #1F6FEB;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#accentBtn:hover {
    background-color: #388BFD;
}
QPushButton#dangerBtn {
    background-color: #DA3633;
    border-color: #F85149;
    color: #FFFFFF;
}
QPushButton#dangerBtn:hover {
    background-color: #B62324;
}
QComboBox {
    background-color: #161B22;
    color: #E6EDF3;
    border: 1px solid #30363D;
    padding: 6px 12px;
    border-radius: 6px;
}
QComboBox:hover {
    border-color: #00E5FF;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #161B22;
    color: #E6EDF3;
    border: 1px solid #30363D;
    selection-background-color: #00897B;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: 0;
}
QLabel {
    color: #E6EDF3;
}
QLabel#titleLabel {
    color: #00E5FF;
    font-size: 16px;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #30363D;
    border-radius: 4px;
    text-align: center;
    background-color: #161B22;
    color: #FFFFFF;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #00E5FF;
    border-radius: 3px;
}
QTabBar::tab {
    background-color: #21262D;
    color: #8B949E;
    border: 1px solid #30363D;
    border-bottom-color: transparent;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #161B22;
    color: #00E5FF;
    border-bottom: 2px solid #00E5FF;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #30363D;
    background-color: #161B22;
    border-radius: 4px;
    padding: 6px;
}
QPlainTextEdit, QTextEdit, QLineEdit {
    background-color: #0D1117;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}
QScrollBar:vertical {
    border: none;
    background: #0D1117;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363D;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #484F58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME = """
QMainWindow {
    background-color: #F6F8FA;
}
QWidget {
    color: #24292F;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QFrame#panelFrame {
    background-color: #FFFFFF;
    border: 1px solid #D0D7DE;
    border-radius: 8px;
}
QFrame#viewportFrame {
    background-color: #EAEEF2;
    border: 1px solid #D0D7DE;
    border-radius: 8px;
}
QFrame#screenSlot {
    background-color: #000000;
    border: 2px solid #00897B;
    border-radius: 6px;
}
QPushButton {
    background-color: #F6F8FA;
    color: #24292F;
    border: 1px solid #D0D7DE;
    padding: 7px 14px;
    border-radius: 6px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #F3F4F6;
    border-color: #8C959F;
}
QPushButton:pressed {
    background-color: #EBEBEB;
}
QPushButton:disabled {
    background-color: #F6F8FA;
    color: #8C959F;
    border-color: #D0D7DE;
}
QPushButton#primaryBtn {
    background-color: #00897B;
    border-color: #00897B;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #00796B;
}
QPushButton#accentBtn {
    background-color: #0969DA;
    border-color: #0969DA;
    color: #FFFFFF;
    font-weight: bold;
}
QPushButton#accentBtn:hover {
    background-color: #0856B7;
}
QPushButton#dangerBtn {
    background-color: #CF222E;
    border-color: #CF222E;
    color: #FFFFFF;
}
QPushButton#dangerBtn:hover {
    background-color: #A40E26;
}
QComboBox {
    background-color: #FFFFFF;
    color: #24292F;
    border: 1px solid #D0D7DE;
    padding: 6px 12px;
    border-radius: 6px;
}
QComboBox:hover {
    border-color: #00897B;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #24292F;
    border: 1px solid #D0D7DE;
    selection-background-color: #00897B;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: 0;
}
QLabel {
    color: #24292F;
}
QLabel#titleLabel {
    color: #00897B;
    font-size: 16px;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #D0D7DE;
    border-radius: 4px;
    text-align: center;
    background-color: #FFFFFF;
    color: #24292F;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #00897B;
    border-radius: 3px;
}
QTabBar::tab {
    background-color: #21262D;
    color: #8B949E;
    border: 1px solid #30363D;
    border-bottom-color: transparent;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #161B22;
    color: #00E5FF;
    border-bottom: 2px solid #00E5FF;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #30363D;
    background-color: #161B22;
    border-radius: 4px;
    padding: 6px;
}
QPlainTextEdit, QTextEdit, QLineEdit {
    background-color: #FFFFFF;
    color: #24292F;
    border: 1px solid #D0D7DE;
    border-radius: 6px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}
QScrollBar:vertical {
    border: none;
    background: #F6F8FA;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #D0D7DE;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #8C959F;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    return DARK_THEME if theme == "dark" else LIGHT_THEME
