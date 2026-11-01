"""QSettings üzerinde tip güvenli kalıcı ayarlar."""

from PyQt5.QtCore import QSettings

from . import APP_NAME

DEFAULTS = {
    "language": "tr",
    "theme": "dark",
    "profile": "s24u",
    "landscape": False,
    "camera": "virtualscene",
    "camera_enabled": True,
    "avd": "",
    "gpu": "swiftshader_indirect",
    "quick_boot": True,
    "boot_timeout": 300,
    "ram_mb": 4096,
    "cpu_cores": 4,
    "image_variant": "google_apis",
    "embed_mode": "child",
    "kill_emulator_on_exit": True,
    "reset_display_on_exit": True,
    "minimize_to_tray": False,
    "check_updates": True,
    "last_update_check": 0.0,
    "license_accepted": False,
    "last_pkg": "",
    "recent_apks": [],
    "gps_lat": 41.0082,
    "gps_lon": 28.9784,
    "logcat_visible": False,
}

MAX_RECENT = 10


class Settings:
    def __init__(self, org: str = APP_NAME, app: str = "APKStudioPlayer"):
        self._qs = QSettings(org, app)

    def get(self, key: str):
        default = DEFAULTS.get(key)
        raw = self._qs.value(key, None)
        if raw is None:
            return list(default) if isinstance(default, list) else default
        try:
            if isinstance(default, bool):
                if isinstance(raw, bool):
                    return raw
                return str(raw).strip().lower() in ("1", "true", "yes", "on")
            if isinstance(default, int):
                return int(raw)
            if isinstance(default, float):
                return float(raw)
            if isinstance(default, list):
                if isinstance(raw, (list, tuple)):
                    return [str(x) for x in raw]
                return [str(raw)] if str(raw) else []
            if isinstance(default, str):
                return str(raw)
        except (TypeError, ValueError):
            return default
        return raw

    def set(self, key: str, value) -> None:
        self._qs.setValue(key, value)

    def raw(self, key: str, default=None):
        return self._qs.value(key, default)

    def add_recent_apk(self, path: str) -> None:
        recent = [p for p in self.get("recent_apks") if p.lower() != path.lower()]
        recent.insert(0, path)
        self.set("recent_apks", recent[:MAX_RECENT])

    def sync(self) -> None:
        self._qs.sync()
