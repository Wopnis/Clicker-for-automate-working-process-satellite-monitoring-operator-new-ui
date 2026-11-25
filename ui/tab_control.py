# ui/tab_control.py
import time
from datetime import datetime
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QGroupBox, QFormLayout, QCheckBox,
    QFileDialog
)

from clicker_worker import ClickerWorker


class ControlTab(QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None

        # ---------- значения статистики (снимок) ----------
        self._start_ts = None
        self._end_ts = None
        self._last_stats = {
            "processed": 0,
            "false": 0,
            "critical": 0,
            "outside": 0,
            "repeats": 0,
        }
        self._pattern_stats = {}
        self._current_mode = "—"
        self._patterns_snapshot = {"alarm": [], "no_auto_close": [], "false_alarm": []}

        # ---------- таймер uptime ----------
        self._uptime_timer = QTimer(self)
        self._uptime_timer.setInterval(1000)
        self._uptime_timer.timeout.connect(self._update_uptime)

        layout = QVBoxLayout()

        # ---------- статус ----------
        status_group = QGroupBox("Статус")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Статус: не запущено")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)

        # ---------- активные паттерны ----------
        summary_group = QGroupBox("Активные паттерны")
        summary_form = QFormLayout()
        self.alarm_count_label = QLabel("0")
        self.no_close_count_label = QLabel("0")
        self.false_count_label = QLabel("0")
        summary_form.addRow("🟥 Автозакрытие (ALARM):", self.alarm_count_label)
        summary_form.addRow("🟨 Без автозакрытия (NO_AUTO_CLOSE):", self.no_close_count_label)
        summary_form.addRow("🟦 Ложная тревога:", self.false_count_label)
        summary_group.setLayout(summary_form)

        # ---------- статистика смены ----------
        stats_group = QGroupBox("📊 Статистика смены")
        stats_form = QFormLayout()

        self.stat_total_label = QLabel("0")
        self.stat_processed_label = QLabel("0")
        self.stat_false_label = QLabel("0")
        self.stat_critical_label = QLabel("0")
        self.stat_outside_label = QLabel("0")
        self.stat_repeats_label = QLabel("0")
        self.stat_uptime_label = QLabel("00:00:00")
        self.stat_speed_label = QLabel("0 / час")

        # Выделяем «Всего тревог» покрупнее
        self.stat_total_label.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #1a73e8;"
        )
        for lbl in (self.stat_processed_label, self.stat_false_label,
                    self.stat_critical_label, self.stat_outside_label,
                    self.stat_repeats_label, self.stat_uptime_label,
                    self.stat_speed_label):
            lbl.setStyleSheet("font-size: 12pt; font-weight: bold;")

        stats_form.addRow("Всего тревог на сайте:", self.stat_total_label)
        stats_form.addRow("  • Закрыл кликер:", self.stat_processed_label)
        stats_form.addRow("     из них ложных:", self.stat_false_label)
        stats_form.addRow("  • Закроет оператор вручную:", self.stat_critical_label)
        stats_form.addRow("  • Закрыто вне кликера:", self.stat_outside_label)
        stats_form.addRow("Повторов тревог:", self.stat_repeats_label)
        stats_form.addRow("Время работы:", self.stat_uptime_label)
        stats_form.addRow("Скорость:", self.stat_speed_label)

        stats_btn_row = QHBoxLayout()
        self.reset_stats_btn = QPushButton("🔄 Сбросить")
        self.save_stats_btn = QPushButton("💾 Сохранить в файл")
        self.save_stats_btn.setEnabled(False)
        self.reset_stats_btn.clicked.connect(self.reset_stats)
        self.save_stats_btn.clicked.connect(self._manual_save_stats)
        stats_btn_row.addWidget(self.reset_stats_btn)
        stats_btn_row.addWidget(self.save_stats_btn)
        stats_btn_row.addStretch()

        stats_layout = QVBoxLayout()
        stats_layout.addLayout(stats_form)
        stats_layout.addLayout(stats_btn_row)
        stats_group.setLayout(stats_layout)

        # ---------- режим запуска ----------
        mode_group = QGroupBox("Режим запуска")
        mode_layout = QVBoxLayout()

        self.mock_checkbox = QCheckBox("🧪 Тестовый режим (без браузера)")
        self.mock_checkbox.setToolTip(
            "Скрипт не открывает сайт AVO.\n"
            "Тревоги генерируются искусственно — только для отладки UI."
        )

        self.auth_only_checkbox = QCheckBox("🔍 Только авторизация (без кликов)")
        self.auth_only_checkbox.setToolTip(
            "Открывает браузер, логинится, сканирует таблицу тревог\n"
            "и НЕ нажимает никакие кнопки. Через 30 секунд закрывается."
        )

        self.mock_checkbox.stateChanged.connect(self._sync_modes)
        self.auth_only_checkbox.stateChanged.connect(self._sync_modes)

        mode_hint = QLabel(
            "Если оба сняты — <b>боевой режим</b> "
            "(полный цикл автозакрытия тревог)."
        )
        mode_hint.setWordWrap(True)

        mode_layout.addWidget(self.mock_checkbox)
        mode_layout.addWidget(self.auth_only_checkbox)
        mode_layout.addWidget(mode_hint)
        mode_group.setLayout(mode_layout)

        # ---------- кнопки управления ----------
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Запустить")
        self.pause_btn = QPushButton("⏸ Пауза")
        self.resume_btn = QPushButton("▶ Продолжить")
        self.stop_btn = QPushButton("⏹ Остановить")

        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self.start)
        self.pause_btn.clicked.connect(self.pause)
        self.resume_btn.clicked.connect(self.resume)
        self.stop_btn.clicked.connect(self.stop)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.resume_btn)
        btn_layout.addWidget(self.stop_btn)

        hint = QLabel(
            "Перед запуском убедитесь, что:\n"
            "• на вкладке «Учётные данные» сохранены логин и пароль;\n"
            "• на вкладке «Тревоги» отмечены нужные паттерны."
        )
        hint.setWordWrap(True)

        layout.addWidget(status_group)
        layout.addWidget(summary_group)
        layout.addWidget(stats_group)
        layout.addWidget(mode_group)
        layout.addLayout(btn_layout)
        layout.addWidget(hint)
        layout.addStretch()
        self.setLayout(layout)

        self.refresh_summary()

    # ---------- public ----------
    def refresh_summary(self):
        alarm = self.config.get_patterns_for_kind("alarm")
        no_close = self.config.get_patterns_for_kind("no_auto_close")
        false = self.config.get_patterns_for_kind("false_alarm")
        self.alarm_count_label.setText(f"{len(alarm)}")
        self.no_close_count_label.setText(f"{len(no_close)}")
        self.false_count_label.setText(f"{len(false)}")

    def reset_stats(self):
        self.stat_total_label.setText("0")
        self.stat_processed_label.setText("0")
        self.stat_false_label.setText("0")
        self.stat_critical_label.setText("0")
        self.stat_outside_label.setText("0")
        self.stat_repeats_label.setText("0")
        self.stat_speed_label.setText("0 / час")
        self._last_stats = {
            "processed": 0, "false": 0, "critical": 0,
            "outside": 0, "repeats": 0,
        }
        self._pattern_stats = {}
        if self._start_ts is None:
            self.stat_uptime_label.setText("00:00:00")

    # ---------- internal ----------
    def _sync_modes(self):
        sender = self.sender()
        if sender is self.mock_checkbox and self.mock_checkbox.isChecked():
            self.auth_only_checkbox.blockSignals(True)
            self.auth_only_checkbox.setChecked(False)
            self.auth_only_checkbox.blockSignals(False)
        elif sender is self.auth_only_checkbox and self.auth_only_checkbox.isChecked():
            self.mock_checkbox.blockSignals(True)
            self.mock_checkbox.setChecked(False)
            self.mock_checkbox.blockSignals(False)

    def _build_config(self):
        return {
            "username": self.config.get_env("MY_USERNAME"),
            "password": self.config.get_env("MY_PASSWORD"),
            "bot_token": self.config.get_env("TELEGRAM_BOT_TOKEN"),
            "chat_id": self.config.get_env("TELEGRAM_CHAT_ID"),
            "alarm_patterns": self.config.get_patterns_for_kind("alarm"),
            "no_auto_close_patterns": self.config.get_patterns_for_kind("no_auto_close"),
            "false_alarm_patterns": self.config.get_patterns_for_kind("false_alarm"),
            "mock": self.mock_checkbox.isChecked(),
            "auth_only": self.auth_only_checkbox.isChecked(),
        }

    def _update_uptime(self):
        if self._start_ts is None:
            return
        elapsed = int(time.time() - self._start_ts)
        hh = elapsed // 3600
        mm = (elapsed % 3600) // 60
        ss = elapsed % 60
        self.stat_uptime_label.setText(f"{hh:02d}:{mm:02d}:{ss:02d}")

        total = int(self.stat_total_label.text())
        if elapsed > 0 and total > 0:
            speed = int(total * 3600 / elapsed)
            self.stat_speed_label.setText(f"{speed} / час")

    # ---------- save stats ----------
    def _collect_report(self) -> dict:
        start_ts = self._start_ts or time.time()
        end_ts = self._end_ts or time.time()
        duration = int(end_ts - start_ts)

        processed = self._last_stats.get("processed", 0)
        false_cnt = self._last_stats.get("false", 0)
        critical = self._last_stats.get("critical", 0)
        outside = self._last_stats.get("outside", 0)
        repeats = self._last_stats.get("repeats", 0)
        total_triggered = processed + critical + outside

        if duration > 0 and total_triggered > 0:
            speed = f"{int(total_triggered * 3600 / duration)} / час"
        else:
            speed = "0 / час"

        return {
            "mode": self._current_mode,
            "start_time": datetime.fromtimestamp(start_ts).strftime("%d.%m.%Y %H:%M:%S"),
            "end_time": datetime.fromtimestamp(end_ts).strftime("%d.%m.%Y %H:%M:%S"),
            "duration_sec": duration,
            "duration_str": self.stat_uptime_label.text(),
            "total_triggered": total_triggered,
            "processed": processed,
            "false": false_cnt,
            "critical": critical,
            "outside": outside,
            "repeats": repeats,
            "speed": speed,
            "patterns_alarm": list(self._patterns_snapshot.get("alarm", [])),
            "patterns_no_close": list(self._patterns_snapshot.get("no_auto_close", [])),
            "patterns_false": list(self._patterns_snapshot.get("false_alarm", [])),
            "pattern_stats": {k: dict(v) for k, v in self._pattern_stats.items()},
        }

    def _format_report_txt(self, r: dict) -> str:
        lines = []
        lines.append("=" * 78)
        lines.append("           ОТЧЁТ О СМЕНЕ — AVO CLICKER")
        lines.append("=" * 78)
        lines.append("")
        lines.append(f"Режим работы:            {r['mode']}")
        lines.append(f"Начало смены:            {r['start_time']}")
        lines.append(f"Окончание смены:         {r['end_time']}")
        lines.append(f"Длительность:            {r['duration_str']}  ({r['duration_sec']} сек)")
        lines.append("")
        lines.append("-" * 78)
        lines.append("                 ОБЩАЯ СТАТИСТИКА")
        lines.append("-" * 78)
        lines.append(f"Всего тревог на сайте:        {r['total_triggered']}")
        lines.append(f"  • Закрыл кликер:            {r['processed']}")
        lines.append(f"     из них ложных:           {r['false']}")
        lines.append(f"  • Закроет оператор вручную: {r['critical']}  (NO_AUTO_CLOSE)")
        lines.append(f"  • Закрыто вне кликера:      {r['outside']}")
        lines.append(f"Повторов тревог за смену:     {r['repeats']}")
        lines.append(f"Скорость:                     {r['speed']}")
        lines.append("")

        pat_stats = r.get("pattern_stats", {})
        if pat_stats:
            lines.append("-" * 78)
            lines.append("          РАЗБИВКА ПО ТИПАМ ТРЕВОГ (по паттернам)")
            lines.append("-" * 78)
            lines.append("")
            lines.append(
                f"{'Паттерн':<34} {'Всего':>6} {'Закр.':>6} {'Ложн.':>6} "
                f"{'Крит.':>6} {'Вне кл.':>8} {'Повт.':>6}"
            )
            lines.append("-" * 78)

            for pattern, st in sorted(
                pat_stats.items(),
                key=lambda kv: kv[1].get("total", 0),
                reverse=True
            ):
                total = st.get("total", 0)
                closed = st.get("closed", 0)
                false = st.get("false", 0)
                critical = st.get("critical", 0)
                outside = st.get("outside", 0)
                repeats = st.get("repeats", 0)
                name = pattern if len(pattern) <= 32 else pattern[:29] + "..."
                lines.append(
                    f"{name:<34} {total:>6} {closed:>6} {false:>6} "
                    f"{critical:>6} {outside:>8} {repeats:>6}"
                )
            lines.append("-" * 78)
            lines.append("")
        else:
            lines.append("Разбивка по паттернам отсутствует — ни один паттерн не сработал.")
            lines.append("")

        lines.append("-" * 78)
        lines.append("         АКТИВНЫЕ ПАТТЕРНЫ НА МОМЕНТ СТАРТА")
        lines.append("-" * 78)
        lines.append("")
        lines.append("[ALARM — автозакрытие]")
        for p in r["patterns_alarm"]:
            lines.append(f"  • {p}")
        if not r["patterns_alarm"]:
            lines.append("  (пусто)")
        lines.append("")
        lines.append("[NO_AUTO_CLOSE — без автозакрытия]")
        for p in r["patterns_no_close"]:
            lines.append(f"  • {p}")
        if not r["patterns_no_close"]:
            lines.append("  (пусто)")
        lines.append("")
        lines.append("[FALSE_ALARM — ложная тревога]")
        for p in r["patterns_false"]:
            lines.append(f"  • {p}")
        if not r["patterns_false"]:
            lines.append("  (пусто)")
        lines.append("")
        lines.append("=" * 78)
        lines.append("Отчёт сформирован автоматически AVO Clicker.")
        lines.append("=" * 78)
        return "\n".join(lines)

    def _format_report_csv(self, r: dict) -> str:
        def esc(s):
            return '"' + str(s).replace('"', '""') + '"'

        lines = []
        lines.append("Параметр;Значение")
        lines.append(f"Режим;{esc(r['mode'])}")
        lines.append(f"Начало смены;{esc(r['start_time'])}")
        lines.append(f"Окончание смены;{esc(r['end_time'])}")
        lines.append(f"Длительность;{esc(r['duration_str'])}")
        lines.append(f"Длительность (сек);{r['duration_sec']}")
        lines.append(f"Всего тревог на сайте;{r['total_triggered']}")
        lines.append(f"Закрыл кликер;{r['processed']}")
        lines.append(f"Из них ложных;{r['false']}")
        lines.append(f"Закроет оператор вручную;{r['critical']}")
        lines.append(f"Закрыто вне кликера;{r['outside']}")
        lines.append(f"Повторов тревог;{r['repeats']}")
        lines.append(f"Скорость;{esc(r['speed'])}")
        lines.append("")

        pat_stats = r.get("pattern_stats", {})
        lines.append("Разбивка по паттернам")
        lines.append("Паттерн;Всего;Закрыто;Ложных;Критических;Закрыто вне кликера;Повторов")
        for pattern, st in sorted(
            pat_stats.items(),
            key=lambda kv: kv[1].get("total", 0),
            reverse=True
        ):
            lines.append(
                f"{esc(pattern)};"
                f"{st.get('total', 0)};"
                f"{st.get('closed', 0)};"
                f"{st.get('false', 0)};"
                f"{st.get('critical', 0)};"
                f"{st.get('outside', 0)};"
                f"{st.get('repeats', 0)}"
            )
        lines.append("")

        lines.append("Активные паттерны на момент старта")
        lines.append("Категория;Паттерн")
        for p in r["patterns_alarm"]:
            lines.append(f"ALARM;{esc(p)}")
        for p in r["patterns_no_close"]:
            lines.append(f"NO_AUTO_CLOSE;{esc(p)}")
        for p in r["patterns_false"]:
            lines.append(f"FALSE_ALARM;{esc(p)}")
        return "\n".join(lines)

    def _manual_save_stats(self):
        if self._start_ts is None:
            QMessageBox.information(self, "Нет данных", "Смена ещё не запускалась.")
            return
        self._save_stats_dialog()

    def _save_stats_dialog(self):
        r = self._collect_report()

        default_name = (
            f"avo_shift_{datetime.fromtimestamp(self._start_ts).strftime('%Y-%m-%d_%H-%M')}"
        )

        filepath, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт о смене",
            default_name,
            "Текстовый файл (*.txt);;CSV для Excel (*.csv)"
        )
        if not filepath:
            return

        try:
            if filepath.lower().endswith(".csv") or "csv" in selected_filter.lower():
                content = self._format_report_csv(r)
                if not filepath.lower().endswith(".csv"):
                    filepath += ".csv"
            else:
                content = self._format_report_txt(r)
                if not filepath.lower().endswith(".txt"):
                    filepath += ".txt"

            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write(content)

            QMessageBox.information(
                self, "Сохранено",
                f"Отчёт сохранён:\n{filepath}"
            )
            self.log_signal.emit("INFO", f"[STATS] Отчёт сохранён: {filepath}")
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка сохранения",
                f"Не удалось сохранить файл:\n{e}"
            )
            self.log_signal.emit("ERROR", f"[STATS] Ошибка сохранения: {e}")

    # ---------- slots ----------
    def start(self):
        is_mock = self.mock_checkbox.isChecked()
        is_auth_only = self.auth_only_checkbox.isChecked()
        needs_browser = not is_mock

        if needs_browser:
            if not self.config.get_env("MY_USERNAME") or not self.config.get_env("MY_PASSWORD"):
                QMessageBox.warning(
                    self, "Нет данных",
                    "Укажите логин и пароль на вкладке «Учётные данные» "
                    "или включите тестовый режим."
                )
                return

        cfg = self._build_config()

        if not (cfg["alarm_patterns"] or cfg["no_auto_close_patterns"] or cfg["false_alarm_patterns"]):
            QMessageBox.warning(
                self, "Пустой набор",
                "Ни один паттерн не отмечен ни в одной колонке на вкладке «Тревоги»."
            )
            return

        self.refresh_summary()
        self.reset_stats()
        self._patterns_snapshot = {
            "alarm": list(cfg["alarm_patterns"]),
            "no_auto_close": list(cfg["no_auto_close_patterns"]),
            "false_alarm": list(cfg["false_alarm_patterns"]),
        }
        self._start_ts = time.time()
        self._end_ts = None
        self._uptime_timer.start()
        self.save_stats_btn.setEnabled(False)

        if is_mock:
            self._current_mode = "🧪 MOCK"
        elif is_auth_only:
            self._current_mode = "🔍 AUTH-ONLY"
        else:
            self._current_mode = "🚀 BOOT (боевой)"

        self.worker = ClickerWorker(cfg)
        self.worker.log_signal.connect(self._on_log)
        self.worker.status_signal.connect(self._on_status)
        self.worker.alarm_signal.connect(lambda t: self.log_signal.emit("ALARM", t))
        self.worker.stats_signal.connect(self._on_stats)
        self.worker.patterns_stats_signal.connect(self._on_patterns_stats)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

        self.status_label.setText(f"Статус: запущено [{self._current_mode}]")
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self.mock_checkbox.setEnabled(False)
        self.auth_only_checkbox.setEnabled(False)

    def pause(self):
        if self.worker:
            self.worker.pause()
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(True)

    def resume(self):
        if self.worker:
            self.worker.resume()
            self.pause_btn.setEnabled(True)
            self.resume_btn.setEnabled(False)

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText("Статус: остановка...")
            self.pause_btn.setEnabled(False)
            self.resume_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    # ---------- worker callbacks ----------
    def _on_log(self, level, msg):
        self.log_signal.emit(level, msg)

    def _on_status(self, text):
        self.status_label.setText(f"Статус: {text}")

    def _on_stats(self, key, value):
        self._last_stats[key] = value
        if key == "processed":
            self.stat_processed_label.setText(str(value))
        elif key == "false":
            self.stat_false_label.setText(str(value))
        elif key == "critical":
            self.stat_critical_label.setText(str(value))
        elif key == "outside":
            self.stat_outside_label.setText(str(value))
        elif key == "repeats":
            self.stat_repeats_label.setText(str(value))

        # пересчёт «Всего тревог на сайте» = processed + critical + outside
        total = (
            self._last_stats.get("processed", 0)
            + self._last_stats.get("critical", 0)
            + self._last_stats.get("outside", 0)
        )
        self.stat_total_label.setText(str(total))

    def _on_patterns_stats(self, data: dict):
        self._pattern_stats = {k: dict(v) for k, v in data.items()}

    def _on_finished(self):
        self.status_label.setText("Статус: остановлено")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.mock_checkbox.setEnabled(True)
        self.auth_only_checkbox.setEnabled(True)

        self._end_ts = time.time()
        self._uptime_timer.stop()
        self._update_uptime()
        self.save_stats_btn.setEnabled(True)

        self._ask_save_on_stop()

    def _ask_save_on_stop(self):
        if self._start_ts is None:
            return

        duration = int((self._end_ts or time.time()) - self._start_ts)
        processed = self._last_stats.get("processed", 0)
        critical = self._last_stats.get("critical", 0)
        outside = self._last_stats.get("outside", 0)
        total = processed + critical + outside

        if duration < 5 and total == 0:
            return

        reply = QMessageBox.question(
            self,
            "Сохранить отчёт?",
            f"Смена завершена.\n\n"
            f"Всего тревог на сайте: {total}\n"
            f"  • Закрыл кликер: {processed}\n"
            f"     из них ложных: {self._last_stats.get('false', 0)}\n"
            f"  • Закроет оператор вручную: {critical}\n"
            f"  • Закрыто вне кликера: {outside}\n"
            f"Повторов тревог: {self._last_stats.get('repeats', 0)}\n\n"
            f"Время работы: {self.stat_uptime_label.text()}\n\n"
            f"Сохранить отчёт в файл?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._save_stats_dialog()