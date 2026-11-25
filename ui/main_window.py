# ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QStatusBar, QApplication
)

from config_manager import ConfigManager
from ui.tab_credentials import CredentialsTab
from ui.tab_alarms import AlarmsTab
from ui.tab_new_pattern import NewPatternTab
from ui.tab_control import ControlTab
from ui.tab_logs import LogsTab

from ui.theme_light import apply_light_theme
from ui.theme_dark import apply_dark_theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVO Clicker — Панель оператора")
        self.resize(1100, 780)

        # ---------- config ----------
        self.config = ConfigManager()

        # ---------- tabs ----------
        self.tabs = QTabWidget()

        self.credentials_tab = CredentialsTab(
            self.config,
            on_theme_toggle=self.apply_theme,
        )
        self.alarms_tab = AlarmsTab(self.config)
        self.new_pattern_tab = NewPatternTab(self.config, self.alarms_tab)
        self.control_tab = ControlTab(self.config)
        self.logs_tab = LogsTab()

        self.tabs.addTab(self.credentials_tab, "🔐 Учётные данные")
        self.tabs.addTab(self.alarms_tab, "⚙️ Тревоги")
        self.tabs.addTab(self.new_pattern_tab, "➕ Новые паттерны")
        self.tabs.addTab(self.control_tab, "▶️ Управление")
        self.tabs.addTab(self.logs_tab, "📜 Логи")

        self.setCentralWidget(self.tabs)

        # ---------- проброс логов ----------
        self.control_tab.log_signal.connect(self.logs_tab.append_log)

        # ---------- обновление счётчиков при переключении вкладок ----------
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # ---------- статус-бар ----------
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов")

        # ---------- применяем сохранённую тему ----------
        self.apply_theme(bool(self.config.get_setting("dark_theme", False)))

    # ---------- theme ----------
    def apply_theme(self, is_dark: bool):
        """Применяет светлую или тёмную тему ко всему приложению."""
        app = QApplication.instance()
        if app is None:
            return
        if is_dark:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)

    # ---------- slots ----------
    def _on_tab_changed(self, index: int):
        widget = self.tabs.widget(index)
        if widget is self.control_tab:
            self.control_tab.refresh_summary()

    # ---------- close ----------
    def closeEvent(self, event):
        worker = self.control_tab.worker if hasattr(self.control_tab, "worker") else None
        if worker is not None and worker.isRunning():
            reply = QMessageBox.question(
                self, "Выход",
                "Скрипт ещё работает. Остановить и выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            worker.stop()
            worker.wait(5000)

        reply = QMessageBox.question(
            self, "Очистка данных",
            "Очистить сохранённые логин и пароль?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.clear_credentials()
            try:
                self.credentials_tab.username_edit.clear()
                self.credentials_tab.password_edit.clear()
            except Exception:
                pass

        event.accept()