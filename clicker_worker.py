# clicker_worker.py
import time
import random
import re
import os
import threading
import importlib
from datetime import datetime
from pathlib import Path

import pytz
import requests
from PyQt6.QtCore import QThread, pyqtSignal

# ------------------------------------------------------------------
# Динамическая загрузка аудио-модуля.
# ------------------------------------------------------------------
def _load_playsound():
    for modname in ("playsound3", "playsound"):
        try:
            mod = importlib.import_module(modname)
            fn = getattr(mod, "playsound", None)
            if callable(fn):
                return fn
        except Exception:
            continue
    return None


playsound = _load_playsound()

BASE_DIR = Path(__file__).resolve().parent
ALERT_SOUND_PATH = BASE_DIR / "alert.mp3"


class ClickerWorker(QThread):
    log_signal = pyqtSignal(str, str)          # (level, message)
    status_signal = pyqtSignal(str)
    alarm_signal = pyqtSignal(str)
    stats_signal = pyqtSignal(str, int)        # (имя_счётчика, значение)
    patterns_stats_signal = pyqtSignal(dict)   # {pattern: {...}}
    finished_signal = pyqtSignal()

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.paused = False
        self.stop_flag = False
        self._last_alert_time = 0

        self.mock = bool(config.get("mock", False))
        self.auth_only = bool(config.get("auth_only", False))

        self.alarm_patterns = self._compile(self.config.get("alarm_patterns", []))
        self.no_auto_close_patterns = self._compile(self.config.get("no_auto_close_patterns", []))
        self.false_alarm_patterns = self._compile(self.config.get("false_alarm_patterns", []))
        
        self.all_patterns = self.alarm_patterns + self.no_auto_close_patterns + self.false_alarm_patterns
        
        self.false_alarm_raw = [
            p.strip().lower() for p in self.config.get("false_alarm_patterns", []) if p.strip()
        ]

        # ---- общие счётчики ----
        self._processed = 0
        self._false = 0
        self._critical = 0
        self._outside = 0
        self._repeats = 0
        self._start_ts = None

        self._counted_total_keys = set()
        self._counted_action_keys = set()
        self._seen_keys = set()

        self._pattern_stats = {}
        self.page = None

    # ---------- helpers ----------
    @staticmethod
    def _compile(items):
        compiled = []
        for s in items:
            try:
                compiled.append(re.compile(s, re.IGNORECASE))
            except re.error:
                pass
        return compiled

    def _log(self, level, msg):
        self.log_signal.emit(level, msg)

    def _emit_stats(self):
        self.stats_signal.emit("processed", self._processed)
        self.stats_signal.emit("false", self._false)
        self.stats_signal.emit("critical", self._critical)
        self.stats_signal.emit("outside", self._outside)
        self.stats_signal.emit("repeats", self._repeats)
        self.patterns_stats_signal.emit(
            {k: dict(v) for k, v in self._pattern_stats.items()}
        )

    def _bump_pattern(self, pattern: str, kind: str, delta: int = 1):
        if not pattern:
            return
        entry = self._pattern_stats.setdefault(
            pattern,
            {"total": 0, "closed": 0, "false": 0,
             "critical": 0, "outside": 0, "repeats": 0}
        )
        entry[kind] = entry.get(kind, 0) + delta

    def get_current_time(self):
        return datetime.now(pytz.timezone("Europe/Moscow")).strftime("%d.%m.%Y %H:%M:%S")

    # ---------- control ----------
    def pause(self):
        self.paused = True
        self._log("INFO", "[*] Скрипт поставлен на паузу.")

    def resume(self):
        self.paused = False
        self._log("INFO", "[*] Скрипт продолжил работу.")

    def stop(self):
        self.stop_flag = True
        self._log("INFO", "[*] Получена команда остановки.")

    # ---------- sound / telegram ----------
    def _play_sound(self):
        if playsound is None or not ALERT_SOUND_PATH.exists():
            return
        now = time.time()
        if now - self._last_alert_time > 5:
            try:
                playsound(str(ALERT_SOUND_PATH))
                self._last_alert_time = now
            except Exception as e:
                self._log("WARNING", f"[!] Не удалось воспроизвести звук: {e}")

    def _send_telegram(self, message: str):
        token = self.config.get("bot_token")
        chat_id = self.config.get("chat_id")
        if not token or not chat_id:
            self._log("WARNING", "[Telegram] Бот или chat_id не заданы.")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        try:
            r = requests.post(url, json=payload, timeout=10)
            res = r.json()
            if res.get("ok"):
                self._log("INFO", "[Telegram] Сообщение отправлено.")
            else:
                self._log("ERROR", f"[Telegram] Ошибка: {res.get('description')}")
        except Exception as e:
            self._log("ERROR", f"[Telegram] Исключение: {e}")

    def _is_false_alarm(self, text: str) -> bool:
        if not text:
            return False
        for p in self.false_alarm_patterns:
            try:
                if p.search(text):
                    return True
            except Exception:
                pass
        norm = re.sub(r"\s+", " ", text).strip().lower()
        for s in self.false_alarm_raw:
            if s and s in norm:
                return True
        return False

    # ==================== NEW SITE HELPERS ====================
    def _extract_contract_number(self):
        for _ in range(6):
            try:
                label = self.page.locator("text='Номер договора лизинга'").first
                if label.count() > 0:
                    parent = label.locator("xpath=..")
                    full_text = parent.inner_text()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    if len(lines) >= 2:
                        val = lines[-1] 
                        if 2 < len(val) < 50:
                            return val
            except Exception:
                pass
            time.sleep(0.5)
        return None

    def _just_clicker(self, row_element, alarm_text="", gosnomer="", contract_num=None):
        try:
            btn_take = self.page.locator("button.base-button", has_text="Взять в работу")
            
            if btn_take.count() == 0 or not btn_take.first.is_visible():
                row_element.click()
                time.sleep(0.5)

            if not contract_num:
                contract_num = self._extract_contract_number()
                
            try:
                btn_take.first.wait_for(state="visible", timeout=5000)
            except Exception:
                self._log("WARNING", "[!] Кнопка 'Взять в работу' не появилась за 5 секунд.")
                return False
            
            btn_take.first.click()
            self._log("INFO", "[+] Кнопка 'Взять в работу' нажата")
            time.sleep(random.uniform(1.0, 1.5))
            return True
                
        except Exception as e:
            self._log("ERROR", f"[!] Ошибка при нажатии 'Взять в работу': {e}")
            return False

    def _close_modal(self):
        try:
            btn_card_close = self.page.locator("button.base-button", has_text="Закрыть тревогу").first
            
            if btn_card_close.count() > 0 and btn_card_close.is_visible():
                btn_card_close.click()
                time.sleep(0.5)
                
                btn_modal_confirm = self.page.locator("dialog.modal-dialog_modal button", has_text="Закрыть тревогу")
                
                if btn_modal_confirm.count() > 0 and btn_modal_confirm.is_visible():
                    btn_modal_confirm.click()
                    self._log("INFO", "[+] Нажата кнопка подтверждения в модальном окне.")
                    time.sleep(0.5)
                else:
                    self._log("WARNING", "[!] Кнопка подтверждения в модальном окне не найдена.")
                
                for _ in range(10):
                    if self.page.locator("dialog.modal-dialog_modal").count() == 0:
                        break
                    time.sleep(0.3)
                
                time.sleep(0.5)
                return True
            else:
                self._log("WARNING", "[!] Кнопка 'Закрыть тревогу' в карточке не найдена.")
                return False
                
        except Exception as e:
            self._log("ERROR", f"[!] Ошибка закрытия: {e}")
            
        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass
        return False

    def _close_false_alarm(self):
        try:
            btn_card_false = self.page.locator("button.base-button", has_text="Ложная тревога").first
            
            if btn_card_false.count() > 0 and btn_card_false.is_visible():
                btn_card_false.click()
                time.sleep(0.5)
                
                btn_modal_confirm = self.page.locator("dialog.modal-dialog_modal button", has_text="Закрыть тревогу")
                if btn_modal_confirm.count() > 0 and btn_modal_confirm.is_visible():
                    btn_modal_confirm.click()
                    self._log("INFO", "[+] Ложная тревога подтверждена в модальном окне.")
                    time.sleep(0.5)
                    
                for _ in range(10):
                    if self.page.locator("dialog.modal-dialog_modal").count() == 0:
                        break
                    time.sleep(0.3)
                    
                time.sleep(0.5)
                return True
            else:
                self._log("INFO", "[!] Кнопка 'Ложная тревога' не найдена, закрываем как обычную.")
                return self._close_modal()
        except Exception as e:
            self._log("ERROR", f"[!] Ошибка закрытия ложной тревоги: {e}")
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
            return False

    # ==================== MOCK ====================
    def _run_mock(self):
        self._log("INFO", "[MOCK] Тестовый режим запущен. Браузер не используется.")
        self.status_signal.emit("MOCK: мониторинг")

        all_active = (
            list(self.config.get("alarm_patterns", []))
            + list(self.config.get("no_auto_close_patterns", []))
            + list(self.config.get("false_alarm_patterns", []))
        )
        if not all_active:
            all_active = ["тестовая тревога"]

        last_pattern = None
        while not self.stop_flag:
            if self.paused:
                time.sleep(1)
                continue

            if last_pattern and random.random() < 0.20:
                pattern = last_pattern
                contract = f"TEST-{random.randint(1000, 9999)}"
            else:
                pattern = random.choice(all_active)
                contract = f"TEST-{random.randint(1000, 9999)}"
                last_pattern = pattern

            is_no_close = any(p.search(pattern) for p in self.no_auto_close_patterns)
            is_false = any(p.search(pattern) for p in self.false_alarm_patterns)

            current_time = self.get_current_time()
            msg = f"[!] {current_time} Тревога: {pattern}, Договор: {contract}"
            self._log("INFO", msg)
            self.alarm_signal.emit(pattern)

            stats_key = f"{contract} | {pattern}"
            key = f"{pattern}|{contract}"
            is_repeat = key in self._seen_keys

            if not is_repeat:
                self._seen_keys.add(key)
                if key not in self._counted_total_keys:
                    self._counted_total_keys.add(key)
                    self._bump_pattern(stats_key, "total")
            else:
                self._repeats += 1
                self._bump_pattern(stats_key, "repeats")
                self._log("INFO", f"[MOCK] ПОВТОР тревоги: {pattern} (Договор: {contract})")

            if is_no_close:
                if key not in self._counted_action_keys:
                    self._counted_action_keys.add(key)
                    self._critical += 1
                    self._bump_pattern(stats_key, "critical")
                    self._log("INFO", f"[MOCK] КРИТИЧЕСКАЯ тревога (NO_AUTO_CLOSE) — уведомляю, НЕ закрываю: {pattern}")
                    threading.Thread(target=self._play_sound, daemon=True).start()
                    threading.Thread(
                        target=self._send_telegram,
                        args=(f"⚠️ [MOCK] КРИТИЧЕСКАЯ ТРЕВОГА\n{msg}",),
                        daemon=True,
                    ).start()
                else:
                    self._log("INFO", f"[MOCK] Повтор критической — только звук/уведомление.")
                    threading.Thread(target=self._play_sound, daemon=True).start()
            else:
                self._log("INFO", f"[MOCK] Нажимаю 'Взять в работу' для {pattern}")
                time.sleep(random.uniform(0.5, 1.2))
                if key not in self._counted_action_keys:
                    self._counted_action_keys.add(key)
                    if is_false:
                        self._false += 1
                        self._bump_pattern(stats_key, "false")
                        self._log("INFO", f"[MOCK] Закрываю как ЛОЖНУЮ тревогу: {pattern}")
                    else:
                        self._log("INFO", f"[MOCK] Закрываю обычным способом: {pattern}")
                    self._processed += 1
                    self._bump_pattern(stats_key, "closed")
                else:
                    self._log("INFO", f"[MOCK] Повтор ALARM — закрыт, в счётчиках уже учтён.")

            self._emit_stats()
            time.sleep(random.uniform(3, 6))

        self._log("INFO", "[MOCK] Тестовый режим остановлен.")

    # ==================== BROWSER ACTIONS ====================
    def _login(self, playwright):
        self.status_signal.emit("Авторизация...")
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        context.clear_cookies()
        self.page = context.new_page()
        
        self.page.set_default_timeout(5000)
        
        self.page.goto("https://fleet.myavo.ru/login")
        self._log("INFO", f"[DEBUG] Открыта страница: {self.page.url}")
        
        try:
            self.page.wait_for_selector('input[placeholder="Введите логин"]', timeout=15000)
            self.page.wait_for_selector('input[placeholder="Введите пароль"]', timeout=15000)
            
            self.page.locator('input[placeholder="Введите логин"]').fill(self.config.get("username") or "")
            self.page.locator('input[placeholder="Введите пароль"]').fill(self.config.get("password") or "")
            
            self.page.locator('button:has-text("Войти")').click()
            self.page.wait_for_timeout(3000)
            
            self._log("INFO", "[+] Авторизация выполнена, переходим на вкладку 'Тревоги'.")
            self.page.goto("https://fleet.myavo.ru/alarms")
            self.page.wait_for_timeout(2000)
            
        except Exception as e:
            self._log("ERROR", f"[!] Ошибка авторизации: {e}")
            try:
                self.page.screenshot(path="login_error.png")
                self._log("INFO", "[!] Скриншот ошибки сохранен в login_error.png")
            except Exception:
                pass
                
        return self.page, context, browser

    # ==================== AUTH ONLY ====================
    def _run_auth_only(self):
        self._log("INFO", "[AUTH-ONLY] Режим 'Только авторизация' активирован.")
        self._log("INFO", "[AUTH-ONLY] Скрипт НЕ будет нажимать никакие кнопки.")
        self.status_signal.emit("AUTH-ONLY: сканирование")

        scan_deadline = time.time() + 30
        found_alarms = 0

        while time.time() < scan_deadline and not self.stop_flag:
            if self.paused:
                time.sleep(1)
                continue

            try:
                rows = self.page.locator(".table-row").all()
            except Exception as e:
                self._log("WARNING", f"[AUTH-ONLY] Не удалось получить строки: {e}")
                time.sleep(2)
                continue

            current_found = 0
            for i, row in enumerate(rows):
                try:
                    status_badge = row.locator(".badge--error")
                    if status_badge.count() == 0 or not status_badge.first.is_visible():
                        continue

                    cells = row.locator(".table-cell-3").all()
                    if len(cells) < 6:
                        continue
                        
                    alarm_text = cells[5].inner_text().strip()
                    gosnomer = cells[3].inner_text().strip()

                    matched = any(p.search(alarm_text) for p in self.all_patterns)
                    if not matched:
                        continue

                    is_no_auto_close = any(p.search(alarm_text) for p in self.no_auto_close_patterns)
                    is_false = self._is_false_alarm(alarm_text)

                    tag = "КРИТИЧНАЯ (не закрывать)" if is_no_auto_close else \
                          "ЛОЖНАЯ" if is_false else "ОБЫЧНАЯ"

                    self._log(
                        "INFO",
                        f"[AUTH-ONLY] {alarm_text} "
                        f"(Госномер: {gosnomer}) → {tag}"
                    )
                    self.alarm_signal.emit(alarm_text)
                    current_found += 1
                except Exception as e:
                    self._log("WARNING", f"[AUTH-ONLY] [{i}] {e}")

            found_alarms = max(found_alarms, current_found)
            time.sleep(2)

        self._log(
            "INFO",
            f"[AUTH-ONLY] Сканирование завершено. "
            f"Обнаружено тревог за проход: {found_alarms}. Клики не производились."
        )

    # ==================== MAIN ====================
    def run(self):
        self._start_ts = time.time()
        self._processed = 0
        self._false = 0
        self._critical = 0
        self._outside = 0
        self._repeats = 0
        self._pattern_stats = {}
        self._seen_keys = set()
        self._counted_total_keys = set()
        self._counted_action_keys = set()
        self._emit_stats()

        if self.mock:
            try:
                self._run_mock()
            except Exception as e:
                self._log("ERROR", f"[MOCK] Исключение: {e}")
            finally:
                self.status_signal.emit("Остановлено")
                self.finished_signal.emit()
            return

        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            self._log("ERROR", f"[FATAL] Не удалось импортировать playwright: {e}")
            self.status_signal.emit("Остановлено")
            self.finished_signal.emit()
            return

        try:
            with sync_playwright() as p:
                page, context, browser = self._login(p)

                if self.auth_only:
                    self._run_auth_only()
                else:
                    self.status_signal.emit("Мониторинг...")
                    self._monitor()

                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass
        except Exception as e:
            self._log("ERROR", f"[FATAL] {e}")
        finally:
            self.status_signal.emit("Остановлено")
            self.finished_signal.emit()

    def _monitor(self):
        active_critical = set()
        self._log("INFO", "Мониторинг запущен (новая версия сайта).")

        while not self.stop_flag:
            if self.paused:
                time.sleep(1)
                continue

            try:
                modal = self.page.locator("dialog.modal-dialog_modal")
                if modal.count() > 0 and modal.first.is_visible():
                    self._log("WARNING", "[!] Обнаружена висящая модалка — нажимаю Escape.")
                    self.page.keyboard.press("Escape")
                    time.sleep(0.5)
            except Exception:
                pass

            try:
                rows = self.page.locator(".table-row").all()
            except Exception as e:
                if self.stop_flag: break
                self._log("WARNING", f"Не удалось получить строки: {e}")
                time.sleep(2)
                continue

            current_critical = set()
            for i, row in enumerate(rows):
                if self.stop_flag:
                    break
                
                try:
                    status_badge = row.locator(".badge--error")
                    if status_badge.count() == 0 or not status_badge.first.is_visible():
                        continue

                    cells = row.locator(".table-cell-3").all()
                    if len(cells) < 6:
                        continue
                        
                    alarm_id = cells[0].inner_text().strip()
                    gosnomer = cells[3].inner_text().strip()
                    alarm_text = cells[5].inner_text().strip()
                    
                    matched = any(p.search(alarm_text) for p in self.all_patterns)
                    if not matched:
                        continue

                    is_no_auto_close = any(p.search(alarm_text) for p in self.no_auto_close_patterns)
                    
                    # Кликаем для получения договора
                    row.click()
                    time.sleep(0.5)
                    contract_num = self._extract_contract_number()
                    
                    if contract_num:
                        stats_key = f"{contract_num} | {alarm_text}"
                        display_msg = f"Договор: {contract_num}, Госномер: {gosnomer}, Тревога: {alarm_text}"
                    else:
                        stats_key = f"{gosnomer} | {alarm_text}"
                        display_msg = f"Госномер: {gosnomer}, Тревога: {alarm_text}"

                    key = f"{alarm_text}|{gosnomer}"
                    current_critical.add(key)

                    if is_no_auto_close:
                        if key not in active_critical:
                            self._critical += 1
                            self._bump_pattern(stats_key, "total")
                            self._bump_pattern(stats_key, "critical")
                            self._emit_stats()
                            
                            # Логируем и шлем уведомление ТОЛЬКО ОДИН РАЗ
                            msg = f"[!] {self.get_current_time()} {display_msg}"
                            self._log("INFO", msg)
                            self.alarm_signal.emit(alarm_text)
                            self._log("INFO", f"[ACTION] КРИТИЧЕСКАЯ тревога (NO_AUTO_CLOSE) — уведомляю, НЕ закрываю.")
                            threading.Thread(target=self._play_sound, daemon=True).start()
                            threading.Thread(
                                target=self._send_telegram,
                                args=(f"⚠️ КРИТИЧЕСКАЯ ТРЕВОГА\n{msg}",),
                                daemon=True,
                            ).start()
                        active_critical.add(key)
                    else:
                        if self.stop_flag: break
                        
                        # Если тревога уже в логах (попадала в active_critical или мы её уже пытались взять) — пропускаем
                        if key in self._counted_action_keys:
                            continue
                            
                        success = self._just_clicker(row, alarm_text, gosnomer, contract_num)
                        
                        if success:
                            msg = f"[!] {self.get_current_time()} {display_msg}"
                            self._log("INFO", msg)
                            self.alarm_signal.emit(alarm_text)
                            
                            self._bump_pattern(stats_key, "total")
                            if self._is_false_alarm(alarm_text):
                                self._close_false_alarm()
                                self._false += 1
                                self._bump_pattern(stats_key, "false")
                            else:
                                self._close_modal()
                            self._processed += 1
                            self._bump_pattern(stats_key, "closed")
                            self._emit_stats()
                            self._counted_action_keys.add(key)
                        else:
                            # Не удалось взять, но логируем один раз
                            msg = f"[!] {self.get_current_time()} {display_msg}"
                            self._log("INFO", msg)
                            self.alarm_signal.emit(alarm_text)
                            
                            self._outside += 1
                            self._bump_pattern(stats_key, "outside")
                            self._emit_stats()
                            self._log("WARNING", "[!] Не удалось взять тревогу. Пауза 5 секунд.")
                            self._counted_action_keys.add(key)
                            time.sleep(5)

                except Exception as e:
                    if self.stop_flag: break
                    self._log("WARNING", f"[{i}] Ошибка обработки строки: {e}")

            active_critical.intersection_update(current_critical)
            
            for _ in range(20):
                if self.stop_flag:
                    break
                time.sleep(0.1)