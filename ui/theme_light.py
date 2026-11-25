# ui/theme_light.py
"""
Светлая тема для приложения.
Применяется функцией apply_light_theme(app) в main.py.
"""

LIGHT_QSS = """
/* ========== Общее ========== */
QWidget {
    background-color: #f5f6f8;
    color: #202124;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
}

QMainWindow, QDialog {
    background-color: #f5f6f8;
}

/* ========== Вкладки ========== */
QTabWidget::pane {
    border: 1px solid #d0d4d9;
    background: #ffffff;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background: #e8eaed;
    color: #3c4043;
    border: 1px solid #d0d4d9;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #1a73e8;
    font-weight: bold;
    border-bottom: 2px solid #1a73e8;
}

QTabBar::tab:hover:!selected {
    background: #f1f3f4;
}

/* ========== Группы (QGroupBox) ========== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #d0d4d9;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #1a73e8;
    background-color: #f5f6f8;
}

/* ========== Поля ввода ========== */
QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QComboBox {
    background-color: #ffffff;
    color: #202124;
    border: 1px solid #c9ccd1;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #1a73e8;
    selection-color: #ffffff;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QListWidget:focus, QComboBox:focus {
    border: 1px solid #1a73e8;
}

QLineEdit:disabled, QComboBox:disabled {
    background-color: #eceff1;
    color: #9aa0a6;
}

/* ========== Кнопки ========== */
QPushButton {
    background-color: #1a73e8;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1765cc;
}

QPushButton:pressed {
    background-color: #1352a8;
}

QPushButton:disabled {
    background-color: #dadce0;
    color: #9aa0a6;
}

/* ========== Чекбоксы ========== */
QCheckBox {
    spacing: 6px;
    padding: 2px 0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #9aa0a6;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border: 1px solid #1a73e8;
}

QCheckBox::indicator:checked {
    background-color: #1a73e8;
    border: 1px solid #1a73e8;
    image: none;
}

QCheckBox::indicator:checked:hover {
    background-color: #1765cc;
}

QCheckBox::indicator:disabled {
    background-color: #eceff1;
    border: 1px solid #dadce0;
}

QCheckBox::indicator:checked:disabled {
    background-color: #b0bec5;
    border: 1px solid #b0bec5;
}

QCheckBox:disabled {
    color: #9aa0a6;
}

/* ========== Скроллбар ========== */
QScrollBar:vertical {
    background: #f1f3f4;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #bdc1c6;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #9aa0a6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #f1f3f4;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #bdc1c6;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #9aa0a6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ========== Статус-бар ========== */
QStatusBar {
    background-color: #e8eaed;
    color: #3c4043;
    border-top: 1px solid #d0d4d9;
}

QStatusBar::item {
    border: none;
}

/* ========== Тултипы ========== */
QToolTip {
    background-color: #202124;
    color: #ffffff;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
}

/* ========== Списки ========== */
QListWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
}

QListWidget::item:selected {
    background-color: #1a73e8;
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: #e8f0fe;
}

/* ========== Скролл в колонках тревог ========== */
QScrollArea {
    border: none;
    background-color: #ffffff;
}
"""


def apply_light_theme(app):
    """Применяет светлую тему ко всему приложению."""
    app.setStyleSheet(LIGHT_QSS)