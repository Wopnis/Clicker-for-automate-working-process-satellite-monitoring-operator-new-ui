# ui/tab_credentials.py
from PyQt6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QLabel, QMessageBox, QGroupBox, QCheckBox
)


class CredentialsTab(QWidget):
    def __init__(self, config, on_theme_toggle=None):
        super().__init__()
        self.config = config
        self.on_theme_toggle = on_theme_toggle

        layout = QVBoxLayout()

        # ---------- Учётные данные ----------
        creds_group = QGroupBox("Учётные данные оператора")
        form = QFormLayout()
        self.username_edit = QLineEdit(config.get_env("MY_USERNAME"))
        self.password_edit = QLineEdit(config.get_env("MY_PASSWORD"))
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.username_edit.setPlaceholderText("Логин от online.myavo.ru")
        self.password_edit.setPlaceholderText("Пароль")
        form.addRow("Логин:", self.username_edit)
        form.addRow("Пароль:", self.password_edit)
        creds_group.setLayout(form)

        # ---------- Telegram ----------
        tg_group = QGroupBox("Telegram-уведомления")
        tg_form = QFormLayout()
        self.bot_token_edit = QLineEdit(config.get_env("TELEGRAM_BOT_TOKEN"))
        self.chat_id_edit = QLineEdit(config.get_env("TELEGRAM_CHAT_ID"))
        self.bot_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        tg_form.addRow("Bot Token:", self.bot_token_edit)
        tg_form.addRow("Chat ID:", self.chat_id_edit)
        tg_group.setLayout(tg_form)

        # ---------- Оформление ----------
        theme_group = QGroupBox("Оформление")
        theme_layout = QVBoxLayout()
        self.dark_theme_checkbox = QCheckBox("🌙 Тёмная тема")
        self.dark_theme_checkbox.setChecked(bool(config.get_setting("dark_theme", False)))
        self.dark_theme_checkbox.stateChanged.connect(self._on_theme_changed)

        theme_hint = QLabel(
            "Переключение темы применяется сразу. "
            "Выбор сохраняется и восстанавливается при следующем запуске."
        )
        theme_hint.setWordWrap(True)

        theme_layout.addWidget(self.dark_theme_checkbox)
        theme_layout.addWidget(theme_hint)
        theme_group.setLayout(theme_layout)

        # ---------- Кнопки ----------
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Сохранить")
        clear_btn = QPushButton("🗑 Очистить логин/пароль")
        save_btn.clicked.connect(self.save)
        clear_btn.clicked.connect(self.clear_credentials)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()

        hint = QLabel(
            "💡 Данные хранятся локально в файле <b>.env</b> в папке программы.<br>"
            "Telegram-токены остаются при очистке учётных данных."
        )
        hint.setWordWrap(True)

        layout.addWidget(creds_group)
        layout.addWidget(tg_group)
        layout.addWidget(theme_group)
        layout.addLayout(btn_layout)
        layout.addWidget(hint)
        layout.addStretch()
        self.setLayout(layout)

    # ---------- handlers ----------
    def _on_theme_changed(self, state):
        is_dark = bool(state)
        self.config.set_setting("dark_theme", is_dark)
        if self.on_theme_toggle:
            self.on_theme_toggle(is_dark)

    def save(self):
        self.config.set_env({
            "MY_USERNAME": self.username_edit.text().strip(),
            "MY_PASSWORD": self.password_edit.text().strip(),
            "TELEGRAM_BOT_TOKEN": self.bot_token_edit.text().strip(),
            "TELEGRAM_CHAT_ID": self.chat_id_edit.text().strip(),
        })
        QMessageBox.information(self, "Сохранено", "Настройки сохранены в .env")

    def clear_credentials(self):
        self.username_edit.clear()
        self.password_edit.clear()
        self.config.clear_credentials()
        QMessageBox.information(self, "Очищено", "Логин и пароль удалены.")