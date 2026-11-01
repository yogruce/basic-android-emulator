"""Merkezi loglama: dönen dosya logu + (kaynak modda) konsol."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .paths import is_frozen, logs_dir

LOG_FILE_NAME = "apkstudio.log"
_configured = False


def log_file() -> str:
    return os.path.join(logs_dir(), LOG_FILE_NAME)


def setup_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)

    fh = RotatingFileHandler(log_file(), maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    if not is_frozen() and sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)

    def _excepthook(exc_type, exc, tb):
        logging.getLogger("uncaught").critical("Yakalanmamış hata", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook
    _configured = True
