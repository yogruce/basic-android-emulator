"""Logcat görüntüleyici widget."""

import re
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QPlainTextEdit, QLabel
)
from PyQt5.QtCore import QThread, pyqtSignal
from ..i18n import T

class LogcatReaderThread(QThread):
    new_line = pyqtSignal(str)

    def __init__(self, adb_path: str, serial: str, parent=None):
        super().__init__(parent)
        self.adb_path = adb_path
        self.serial = serial
        self._running = True
        self._proc = None

    def run(self):
        # logcat -v time
        cmd = [self.adb_path, "-s", self.serial, "logcat", "-v", "time"]
        no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=no_window
            )
            while self._running and self._proc.poll() is None:
                line = self._proc.stdout.readline()
                if line:
                    self.new_line.emit(line.rstrip())
                else:
                    break
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


class LogcatWidget(QWidget):
    def __init__(self, adb_client, parent=None):
        super().__init__(parent)
        self.adb = adb_client
        self.reader = None
        self.target_pid = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Filtre çubuğu
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText(T("Filtrele (metin, tag, paket)...", "Filter (text, tag, package)..."))
        self.filter_input.textChanged.connect(self.on_filter_changed)
        top_bar.addWidget(self.filter_input)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["Verbose", "Debug", "Info", "Warn", "Error", "Assert"])
        self.level_combo.setCurrentText("Verbose")
        self.level_combo.currentIndexChanged.connect(self.on_filter_changed)
        top_bar.addWidget(self.level_combo)

        btn_clear = QPushButton(T("Temizle", "Clear"))
        btn_clear.clicked.connect(self.clear_logs)
        top_bar.addWidget(btn_clear)

        layout.addLayout(top_bar)

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setMaximumBlockCount(3000)
        layout.addWidget(self.text_area)

    def set_target_package(self, pkg_name: str):
        if not pkg_name or not self.adb.is_online():
            return
        # pidof pkg_name
        pid = self.adb.pidof(pkg_name)
        if pid:
            self.target_pid = pid
            self.filter_input.setText(pid)

    def start_logging(self):
        self.stop_logging()
        if not self.adb.is_online():
            return
        # Önceki logları temizle
        self.adb.shell("logcat", "-c")
        self.reader = LogcatReaderThread(self.adb.adb_path, self.adb.serial, self)
        self.reader.new_line.connect(self.handle_line)
        self.reader.start()

    def stop_logging(self):
        if self.reader:
            self.reader.stop()
            self.reader.wait(1000)
            self.reader = None

    def handle_line(self, line: str):
        if self.matches_filter(line):
            self.text_area.appendPlainText(line)

    def matches_filter(self, line: str) -> bool:
        # Seviye filtresi: V/, D/, I/, W/, E/, A/
        level = self.level_combo.currentText()[0]
        levels = ["V", "D", "I", "W", "E", "A"]
        idx_cur = levels.index(level) if level in levels else 0

        # Basit seviye kontrolü
        match_level = False
        for i in range(idx_cur, len(levels)):
            if f" {levels[i]}/" in line or f"/{levels[i]} " in line or line.startswith(f"{levels[i]}/"):
                match_level = True
                break
        if not match_level and idx_cur > 0:
            return False

        # Metin filtresi
        flt = self.filter_input.text().strip()
        if flt and flt.lower() not in line.lower():
            return False
        return True

    def on_filter_changed(self):
        pass

    def clear_logs(self):
        self.text_area.clear()
        if self.adb.is_online():
            self.adb.shell("logcat", "-c")
