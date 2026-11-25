# ui/tab_logs.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QComboBox
)
from PyQt6.QtGui import QTextCursor
from datetime import datetime


class LogsTab(QWidget):
    MAX_LINES = 5000

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        ctrl = QHBoxLayout()
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Все", "INFO", "WARNING", "ERROR", "ALARM"])
        clear_btn = QPushButton("🗑 Очистить")
        clear_btn.clicked.connect(lambda: self.text_area.clear())
        ctrl.addWidget(self.level_combo)
        ctrl.addWidget(clear_btn)
        ctrl.addStretch()

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setMaximumBlockCount(self.MAX_LINES)

        layout.addLayout(ctrl)
        layout.addWidget(self.text_area)
        self.setLayout(layout)

    def append_log(self, level: str, message: str):
        # фильтр
        filt = self.level_combo.currentText()
        if filt != "Все" and filt != level:
            return

        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}"
        self.text_area.appendPlainText(line)
        self.text_area.moveCursor(QTextCursor.MoveOperation.End)