# ui/tab_new_pattern.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QMessageBox, QListWidget
)


class NewPatternTab(QWidget):
    def __init__(self, config, alarms_tab):
        super().__init__()
        self.config = config
        self.alarms_tab = alarms_tab

        layout = QVBoxLayout()

        label = QLabel(
            "Добавьте новый паттерн тревоги. Он появится во всех трёх "
            "колонках вкладки «Тревоги» в <b>неактивном</b> состоянии — "
            "там отметьте нужную колонку."
        )
        label.setWordWrap(True)

        # ---------- форма добавления ----------
        form_layout = QHBoxLayout()
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText(
            "Например: 'нет связи > 60 мин' или regex: 'разряд.*аккумулятора'"
        )
        self.pattern_edit.returnPressed.connect(self.add_pattern)

        add_btn = QPushButton("➕ Добавить")
        add_btn.clicked.connect(self.add_pattern)

        form_layout.addWidget(QLabel("Паттерн:"))
        form_layout.addWidget(self.pattern_edit, 1)
        form_layout.addWidget(add_btn)

        # ---------- список существующих ----------
        self.list_widget = QListWidget()
        self._refresh_list()

        del_btn = QPushButton("🗑 Удалить выбранный паттерн")
        del_btn.clicked.connect(self.delete_pattern)

        layout.addWidget(label)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Существующие паттерны:"))
        layout.addWidget(self.list_widget)
        layout.addWidget(del_btn)
        self.setLayout(layout)

    # ---------- internal ----------
    def _refresh_list(self):
        """Пересобирает список всех паттернов с указанием их назначения."""
        self.list_widget.clear()
        for pattern in self.config.get_all_patterns():
            kind = self.config.get_assignment(pattern)
            if kind == "alarm":
                label = "🟥 ALARM"
            elif kind == "no_auto_close":
                label = "🟨 NO_AUTO_CLOSE"
            elif kind == "false_alarm":
                label = "🟦 ЛОЖНАЯ"
            else:
                label = "— не активен"
            self.list_widget.addItem(f"{pattern}   [{label}]")

    # ---------- slots ----------
    def add_pattern(self):
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Пусто", "Введите паттерн.")
            return
        ok = self.config.add_pattern(pattern)
        if not ok:
            QMessageBox.warning(self, "Дубликат", "Такой паттерн уже есть.")
            return

        # добавляем чекбокс во все три колонки (нейтрально)
        self.alarms_tab.add_pattern_to_all_groups(pattern)

        self.pattern_edit.clear()
        self._refresh_list()

        QMessageBox.information(
            self, "Готово",
            "Паттерн добавлен. Отметьте его в нужной колонке на вкладке «Тревоги»."
        )

    def delete_pattern(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Не выбрано", "Выберите паттерн из списка.")
            return

        # Отрезаем хвост "   [kind]"
        text = item.text()
        pattern = text.split("   [")[0].strip()

        reply = QMessageBox.question(
            self, "Удалить паттерн?",
            f"Удалить '{pattern}' из всех колонок?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.config.remove_pattern(pattern):
            # Полная перестройка вкладки «Тревоги» (убрать чекбоксы)
            self.alarms_tab.reload_patterns()
            self._refresh_list()
            QMessageBox.information(self, "Удалено", f"Паттерн '{pattern}' удалён.")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось удалить паттерн.")