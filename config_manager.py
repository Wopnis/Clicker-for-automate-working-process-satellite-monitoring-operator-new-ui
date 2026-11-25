# config_manager.py
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
PATTERNS_PATH = BASE_DIR / "patterns.json"
SETTINGS_PATH = BASE_DIR / "settings.json"

# ---------- Дефолтный список паттернов (при первом запуске) ----------
DEFAULT_PATTERNS = [
    "отключение питания ТС",
    "разряд аккумулятора ТС",
    "передвижение с блокировкой",
    "передвижение без зажигания",
    "передвижение без АКБ",
    "въезд в зону: Московская обл.",
    "передвижение с финансовой блокировкой",
    "нет связи > 180 мин",
    "нет связи > 720 мин",
    "выезд из зоны",
    "въезд в зону",
    "нет связи > 4320 мин",
]

# ---------- Дефолтные назначения ----------
DEFAULT_ASSIGNMENTS = {
    "отключение питания ТС": "alarm",
    "разряд аккумулятора ТС": "alarm",
    "передвижение с блокировкой": "alarm",
    "передвижение без зажигания": "alarm",
    "передвижение без АКБ": "alarm",
    "въезд в зону: Московская обл.": "alarm",
    "передвижение с финансовой блокировкой": "alarm",
    "нет связи > 180 мин": "alarm",
    "нет связи > 720 мин": "alarm",
    "выезд из зоны": "no_auto_close",
    "въезд в зону": "no_auto_close",
    "нет связи > 4320 мин": "no_auto_close",
}

KINDS = ("alarm", "no_auto_close", "false_alarm")

# ---------- Дефолтные настройки приложения ----------
DEFAULT_SETTINGS = {
    "dark_theme": False,
}


class ConfigManager:
    """
    Хранит:
      - .env          (логин/пароль/telegram)
      - patterns.json (all_patterns + assignments)
      - settings.json (тема и прочие настройки UI)
    """

    def __init__(self):
        self._env = {}
        self._all_patterns = []
        self._assignments = {}
        self._settings = dict(DEFAULT_SETTINGS)
        self.load_env()
        self.load_patterns()
        self.load_settings()

    # ==================== .env ====================
    def load_env(self):
        if ENV_PATH.exists():
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    self._env[k.strip()] = v.strip()

    def get_env(self, key, default=""):
        return self._env.get(key, default)

    def set_env(self, data: dict):
        self._env.update(data)
        self.save_env()

    def save_env(self):
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            for k, v in self._env.items():
                f.write(f"{k}={v}\n")

    def clear_credentials(self):
        for key in ("MY_USERNAME", "MY_PASSWORD"):
            self._env.pop(key, None)
        self.save_env()

    # ==================== patterns.json ====================
    def load_patterns(self):
        # --- Файла нет: инициализируем дефолтом ---
        if not PATTERNS_PATH.exists():
            self._all_patterns = list(DEFAULT_PATTERNS)
            self._assignments = {p: DEFAULT_ASSIGNMENTS.get(p) for p in self._all_patterns}
            self.save_patterns()
            return

        # --- Файл есть: пробуем прочитать ---
        try:
            with open(PATTERNS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        # --- Новый формат {"all_patterns": [...], "assignments": {...}} ---
        if "all_patterns" in data and "assignments" in data:
            self._all_patterns = list(data.get("all_patterns", []))
            raw_assign = data.get("assignments", {}) or {}
            self._assignments = {}
            for p in self._all_patterns:
                v = raw_assign.get(p)
                self._assignments[p] = v if v in KINDS else None

            # ⭐ Добираем недостающие паттерны из DEFAULT_PATTERNS
            existing_lower = {p.lower() for p in self._all_patterns}
            added = False
            for p in DEFAULT_PATTERNS:
                if p.lower() not in existing_lower:
                    self._all_patterns.append(p)
                    self._assignments[p] = DEFAULT_ASSIGNMENTS.get(p)
                    added = True
            if added:
                self.save_patterns()
            return

        # --- Старый формат {"alarm": [...], "no_auto_close": [...], "false_alarm": [...]} ---
        migrated_all = set()
        migrated_assign = {}

        for kind in KINDS:
            items = data.get(kind, []) or []
            for p in items:
                p = p.strip()
                if not p:
                    continue
                migrated_all.add(p)
                if p not in migrated_assign:
                    migrated_assign[p] = kind

        for p in DEFAULT_PATTERNS:
            migrated_all.add(p)
            if p not in migrated_assign:
                migrated_assign[p] = DEFAULT_ASSIGNMENTS.get(p)

        self._all_patterns = sorted(migrated_all, key=lambda s: s.lower())
        self._assignments = {p: migrated_assign.get(p) for p in self._all_patterns}
        self.save_patterns()

    def save_patterns(self):
        with open(PATTERNS_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "all_patterns": self._all_patterns,
                    "assignments": self._assignments,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    # ==================== публичный API паттернов ====================
    def get_all_patterns(self):
        return list(self._all_patterns)

    def get_assignment(self, pattern: str):
        return self._assignments.get(pattern)

    def get_patterns_for_kind(self, kind: str):
        return [p for p in self._all_patterns if self._assignments.get(p) == kind]

    # Совместимость со старым API
    def get_patterns(self, kind: str):
        return self.get_patterns_for_kind(kind)

    def assign_pattern(self, pattern: str, kind):
        if pattern not in self._all_patterns:
            return
        if kind is not None and kind not in KINDS:
            return
        self._assignments[pattern] = kind
        self.save_patterns()

    def add_pattern(self, pattern: str):
        pattern = pattern.strip()
        if not pattern:
            return False
        if pattern in self._all_patterns:
            return False
        self._all_patterns.append(pattern)
        self._assignments[pattern] = None  # нейтрально
        self.save_patterns()
        return True

    def remove_pattern(self, pattern: str):
        if pattern in self._all_patterns:
            self._all_patterns.remove(pattern)
            self._assignments.pop(pattern, None)
            self.save_patterns()
            return True
        return False

    # ==================== settings.json ====================
    def load_settings(self):
        if not SETTINGS_PATH.exists():
            self.save_settings()
            return
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # объединяем с дефолтными — на случай отсутствующих ключей
                merged = dict(DEFAULT_SETTINGS)
                merged.update(data)
                self._settings = merged
        except Exception:
            pass

    def save_settings(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        self._settings[key] = value
        self.save_settings()