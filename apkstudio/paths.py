"""Uygulama dizinleri: kaynak/EXE kökü, paketlenmiş kaynaklar, kullanıcı veri dizini."""

import os
import sys

from . import APP_NAME


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> str:
    """EXE'nin bulunduğu klasör ya da kaynak kodda proje kökü."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundle_dir() -> str:
    """PyInstaller tek dosya modunda geçici açılan dizin (_MEIPASS), aksi halde proje kökü."""
    return getattr(sys, "_MEIPASS", app_root())


def bundled_bin_dir() -> str:
    return os.path.join(bundle_dir(), "bin")


def _ensure(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def local_appdata() -> str:
    return os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")


def data_dir() -> str:
    """%LOCALAPPDATA%\\APKStudio - loglar, güncellenmiş scrcpy, geçici dosyalar."""
    return _ensure(os.path.join(local_appdata(), APP_NAME))


def runtime_bin_dir() -> str:
    """Çalışma anında kullanılan scrcpy kopyası (güncellemeler buraya iner)."""
    return os.path.join(data_dir(), "bin")


def logs_dir() -> str:
    return _ensure(os.path.join(data_dir(), "logs"))


def temp_dir() -> str:
    return _ensure(os.path.join(data_dir(), "tmp"))


def media_dir() -> str:
    """Ekran görüntüsü ve kayıtların kaydedileceği klasör."""
    pictures = os.path.join(os.path.expanduser("~"), "Pictures")
    return _ensure(os.path.join(pictures, APP_NAME))


def icon_path() -> str:
    for base in (bundled_bin_dir(), os.path.join(app_root(), "bin")):
        p = os.path.join(base, "icon.png")
        if os.path.exists(p):
            return p
    return ""
