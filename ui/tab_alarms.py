# ui/tab_alarms.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QScrollArea, QPushButton, QLabel
)

KIND_TITLES = {
    "alarm": "🟥 Автозакрытие (ALARM)",
    "no_auto_close": "🟨 Без автозакрытия (NO_AUTO_CLOSE)",
    "false_alarm": "🟦 Ложная тревога",
}


class PatternCheckboxGroup(QGroupBox):
    """
    Одна колонка вкладки «Тревоги».
    Показывает ВСЕ паттерны приложения (полный список).
    Чекбокс отмечен и активен → паттерн назначен этому kind.
    Чекбокс снят и активен     → паттерн нейтральный (нигде не назначен).
    Чекбокс снят и disabled    → паттерн назначен другой колонке.
    """

    # (pattern, new_kind | None)
    changed = pyqtSignal(str, object)

    def __init__(self, kind: str, config):
        super().__init__(KIND_TITLES[kind])
        self.kind = kind
        self.config = config
        self.checkboxes = {}

        outer = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self.inner_layout = QVBoxLayout(inner)
        self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for pattern in config.get_all_patterns():
            self._add_checkbox(pattern)

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        self.setLayout(outer)

        self.refresh()

    # ---------- internal ----------
    def _add_checkbox(self, pattern: str):
        if pattern in self.checkboxes:
            return
        cb = QCheckBox(pattern)
        cb.stateChanged.connect(lambda state, p=pattern: self._on_click(p, state))
        self.checkboxes[pattern] = cb
        self.inner_layout.addWidget(cb)

    def _on_click(self, pattern: str, state: int):
        # state: 0 = unchecked, 2 = checked
        if state == Qt.CheckState.Checked.value:
            self.changed.emit(pattern, self.kind)
        else:
            self.changed.emit(pattern, None)

    # ---------- public ----------
    def add_new_pattern(self, pattern: str):
        """Добавляет новый чекбокс (нейтральный), не пересобирая всю колонку."""
        self._add_checkbox(pattern)
        self.refresh()

    def refresh(self):
        """Синхронизирует визуальное состояние чекбоксов с config."""
        for pattern, cb in self.checkboxes.items():
            assigned = self.config.get_assignment(pattern)
            cb.blockSignals(True)
            if assigned == self.kind:
                cb.setChecked(True)
                cb.setEnabled(True)
            elif assigned is None:
                cb.setChecked(False)
                cb.setEnabled(True)
            else:
                cb.setChecked(False)
                cb.setEnabled(False)
            cb.blockSignals(False)

    def rebuild(self):
        """Полная перестройка колонки (после удаления/добавления паттернов)."""
        for cb in self.checkboxes.values():
            cb.setParent(None)
        self.checkboxes.clear()
        for pattern in self.config.get_all_patterns():
            self._add_checkbox(pattern)
        self.refresh()


class AlarmsTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config

        layout = QVBoxLayout()

        hint = QLabel(
            "Каждый паттерн может быть активен только в <b>одной</b> колонке. "
            "Клик по чекбоксу — назначить; повторный клик по уже отмеченному — "
            "снять назначение (паттерн станет неактивным). "
            "Серые (недоступные) чекбоксы назначены в другой колонке."
        )
        hint.setWordWrap(True)

        columns = QHBoxLayout()
        self.alarm_group = PatternCheckboxGroup("alarm", config)
        self.no_close_group = PatternCheckboxGroup("no_auto_close", config)
        self.false_group = PatternCheckboxGroup("false_alarm", config)

        for grp in (self.alarm_group, self.no_close_group, self.false_group):
            grp.changed.connect(self._on_assignment_changed)

        columns.addWidget(self.alarm_group)
        columns.addWidget(self.no_close_group)
        columns.addWidget(self.false_group)

        layout.addWidget(hint)
        layout.addLayout(columns)
        self.setLayout(layout)

    # ---------- handlers ----------
    def _on_assignment_changed(self, pattern: str, kind):
        """Клик по чекбоксу в одной из колонок."""
        self.config.assign_pattern(pattern, kind)
        for grp in (self.alarm_group, self.no_close_group, self.false_group):
            grp.refresh()

    # ---------- API для вкладки «Новые паттерны» ----------
    def add_pattern_to_all_groups(self, pattern: str):
        """Новый паттерн — добавляем чекбокс во все три колонки."""
        for grp in (self.alarm_group, self.no_close_group, self.false_group):
            grp.add_new_pattern(pattern)

    def reload_patterns(self):
        """Полная перестройка всех колонок (после удаления паттерна)."""
        for grp in (self.alarm_group, self.no_close_group, self.false_group):
            grp.rebuild()

    # ---------- совместимость ----------
    def get_selected(self):
        """Возвращает три непересекающихся списка (для ClickerWorker)."""
        return {
            "alarm": self.config.get_patterns_for_kind("alarm"),
            "no_auto_close": self.config.get_patterns_for_kind("no_auto_close"),
            "false_alarm": self.config.get_patterns_for_kind("false_alarm"),
        }