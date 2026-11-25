# ui/theme_dark.py
"""
Тёмная тема для приложения.
Применяется функцией apply_dark_theme(app) в main_window.
"""

DARK_QSS = """
/* ========== Общее ========== */
QWidget {
    background-color: #1e1f22;
    color: #e3e3e3;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 10pt;
}

QMainWindow, QDialog {
    background-color: #1e1f22;
}

/* ========== Вкладки ========== */
QTabWidget::pane {
    border: 1px solid #3c4043;
    background: #2b2d30;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background: #2b2d30;
    color: #b0b0b0;
    border: 1px solid #3c4043;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background: #3c4043;
    color: #8ab4f8;
    font-weight: bold;
    border-bottom: 2px solid #8ab4f8;
}

QTabBar::tab:hover:!selected {
    background: #35373b;
}

/* ========== Группы ========== */
QGroupBox {
    background-color: #2b2d30;
    border: 1px solid #3c4043;
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
    color: #8ab4f8;
    background-color: #1e1f22;
}

/* ========== Поля ввода ========== */
QLineEdit, QPlainTextEdit, QTextEdit, QListWidget, QComboBox {
    background-color: #1e1f22;
    color: #e3e3e3;
    border: 1px solid #3c4043;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #8ab4f8;
    selection-color: #1e1f22;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QListWidget:focus, QComboBox:focus {
    border: 1px solid #8ab4f8;
}

QLineEdit:disabled, QComboBox:disabled {
    background-color: #2b2d30;
    color: #6b6b6b;
}

/* ========== Кнопки ========== */
QPushButton {
    background-color: #8ab4f8;
    color: #1e1f22;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #aecbfa;
}

QPushButton:pressed {
    background-color: #6a9be0;
}

QPushButton:disabled {
    background-color: #3c4043;
    color: #6b6b6b;
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
    border: 1px solid #6b6b6b;
    background-color: #1e1f22;
}

QCheckBox::indicator:hover {
    border: 1px solid #8ab4f8;
}

QCheckBox::indicator:checked {
    background-color: #8ab4f8;
    border: 1px solid #8ab4f8;
    image: none;
}

QCheckBox::indicator:checked:hover {
    background-color: #aecbfa;
}

QCheckBox::indicator:disabled {
    background-color: #2b2d30;
    border: 1px solid #3c4043;
}

QCheckBox::indicator:checked:disabled {
    background-color: #4a5a6a;
    border: 1px solid #4a5a6a;
}

QCheckBox:disabled {
    color: #6b6b6b;
}

/* ========== Скроллбар ========== */
QScrollBar:vertical {
    background: #1e1f22;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #3c4043;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #5a5d61;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #1e1f22;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #3c4043;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #5a5d61;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ========== Статус-бар ========== */
QStatusBar {
    background-color: #2b2d30;
    color: #b0b0b0;
    border-top: 1px solid #3c4043;
}

QStatusBar::item {
    border: none;
}

/* ========== Тултипы ========== */
QToolTip {
    background-color: #3c4043;
    color: #e3e3e3;
    border: 1px solid #5a5d61;
    padding: 4px 8px;
    border-radius: 4px;
}

/* ========== Списки ========== */
QListWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
}

QListWidget::item:selected {
    background-color: #8ab4f8;
    color: #1e1f22;
}

QListWidget::item:hover:!selected {
    background-color: #35373b;
}

/* ========== Скролл в колонках тревог ========== */
QScrollArea {
    border: none;
    background-color: #2b2d30;
}
"""


def apply_dark_theme(app):
    app.setStyleSheet(DARK_QSS)