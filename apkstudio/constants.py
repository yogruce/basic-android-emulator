"""Sabitler: cihaz profilleri, kamera modları, GPU modları, ağ profilleri."""

from .i18n import T

EMULATOR_PORT = 5588  # 5554-5682 aralığında çift sayı olmalı
DEVICE_SERIAL = f"emulator-{EMULATOR_PORT}"


def device_profiles() -> dict:
    """Profil adı -> {res: 'WxH' (dikey yön), dpi}. Ekran alanı en-boy oranına göre ölçeklenir."""
    return {
        T("Samsung Galaxy S24 Ultra (Telefon 19.5:9)", "Samsung Galaxy S24 Ultra (Phone 19.5:9)"): {"res": "886x1920", "dpi": "340"},
        T("Google Pixel 8 Pro (Telefon 20:9)", "Google Pixel 8 Pro (Phone 20:9)"): {"res": "864x1920", "dpi": "340"},
        T("Samsung Galaxy Tab S9 (Tablet 16:10)", "Samsung Galaxy Tab S9 (Tablet 16:10)"): {"res": "1200x1920", "dpi": "240"},
        T("iPad Pro 11 Tarzı (Tablet 4:3)", "iPad Pro 11 Style (Tablet 4:3)"): {"res": "1440x1920", "dpi": "260"},
        T("Oyun & Kiosk Ekranı (16:9 1080p)", "Gaming & Kiosk Screen (16:9 1080p)"): {"res": "1080x1920", "dpi": "240"},
    }


def profile_keys() -> list:
    """Kalıcı ayar için dil bağımsız anahtarlar (sıra device_profiles ile aynı)."""
    return ["s24u", "pixel8pro", "tabs9", "ipad11", "kiosk1080"]


def camera_modes() -> dict:
    return {
        "webcam0": T("PC Webcam (webcam0 - Gerçek/OBS Kamera)", "PC Webcam (webcam0 - Real/OBS Camera)"),
        "virtualscene": T("Sanal Kamera (virtualscene - 3D Sahne)", "Virtual Camera (virtualscene - 3D Scene)"),
        "emulated": T("Test Deseni (emulated)", "Test Pattern (emulated)"),
        "none": T("Kamera Donanımı Yok (none)", "No Camera Hardware (none)"),
    }


def gpu_modes() -> dict:
    return {
        "auto": T("Otomatik (önerilen)", "Automatic (recommended)"),
        "host": T("Ekran kartı (host) - en hızlı", "Host GPU - fastest"),
        "angle_indirect": "ANGLE (DirectX)",
        "swiftshader_indirect": T("Yazılımsal (SwiftShader) - en uyumlu", "Software (SwiftShader) - most compatible"),
    }


def network_speeds() -> dict:
    return {
        "full": T("Sınırsız", "Unlimited"),
        "lte": "LTE (4G)",
        "hsdpa": "HSDPA (3.5G)",
        "umts": "UMTS (3G)",
        "edge": "EDGE (2.5G)",
        "gsm": "GSM (2G)",
    }


def network_delays() -> dict:
    return {
        "none": T("Gecikme yok", "No latency"),
        "lte": "LTE (~20 ms)",
        "umts": "UMTS (~100 ms)",
        "edge": "EDGE (~150 ms)",
        "gprs": "GPRS (~300 ms)",
    }


GPS_PRESETS = {
    "İstanbul": (41.0082, 28.9784),
    "Ankara": (39.9334, 32.8597),
    "İzmir": (38.4237, 27.1428),
    "London": (51.5072, -0.1276),
    "New York": (40.7128, -74.0060),
    "Tokyo": (35.6762, 139.6503),
}

APK_EXTENSIONS = (".apk", ".apks", ".xapk", ".apkm")
