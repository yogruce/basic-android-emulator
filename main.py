"""APK Studio Player - Giriş Noktası."""

import os
import sys
import ctypes
from PyQt5.QtWidgets import QApplication

from apkstudio.log import setup_logging
from apkstudio.settings import Settings
from apkstudio.i18n import set_language
from apkstudio.ui.main_window import MainWindow

def main():
    # 1. Loglama Kurulumu
    setup_logging()

    # 2. Kalıcı Ayarlar ve Dil
    settings = Settings()
    set_language(settings.get("language"))

    # 3. Windows DPI ve QT Yapılandırması
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1"
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # 4. Qt Uygulamasını Başlat
    app = QApplication(sys.argv)
    window = MainWindow(settings)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
