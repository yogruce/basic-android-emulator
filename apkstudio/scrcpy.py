"""scrcpy ikili dosya yönetimi, güncelleme ve ekranın ana pencereye gömülmesi."""

import json
import logging
import os
import re
import shutil
import zipfile

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from . import proc, win32
from .downloader import download, fetch_text
from .paths import bundled_bin_dir, logs_dir, runtime_bin_dir, temp_dir

log = logging.getLogger(__name__)

LATEST_RELEASE_API = "https://api.github.com/repos/Genymobile/scrcpy/releases/latest"
VERSION_FILE = "VERSION"
WINDOW_TITLE = "APK_Studio_Docked_Screen"


def _vtuple(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:3]) or (0,)


def read_version(bin_dir: str) -> str:
    vf = os.path.join(bin_dir, VERSION_FILE)
    if os.path.exists(vf):
        with open(vf, encoding="utf-8") as f:
            return f.read().strip()
    exe = os.path.join(bin_dir, "scrcpy.exe")
    if os.path.exists(exe):
        m = re.search(r"scrcpy\s+v?([\d.]+)", proc.run([exe, "--version"], timeout=15).stdout or "")
        if m:
            return m.group(1)
    return ""


def _valid(bin_dir: str) -> bool:
    return all(os.path.exists(os.path.join(bin_dir, f)) for f in ("scrcpy.exe", "scrcpy-server"))


def ensure_runtime_bin() -> str:
    """Paketlenmiş scrcpy'yi kullanıcı veri dizinine eşitler; kullanılacak bin klasörünü döndürür.

    EXE geçici dizinden çalıştığında adb/scrcpy süreçlerinin dosya kilitlemesi önlenir ve
    güncellemeler EXE'yi yeniden derlemeden uygulanabilir.
    """
    bundled, runtime = bundled_bin_dir(), runtime_bin_dir()
    if not _valid(bundled):
        return runtime if _valid(runtime) else bundled
    bv, rv = read_version(bundled), read_version(runtime) if _valid(runtime) else ""
    if not rv or _vtuple(rv) < _vtuple(bv):
        try:
            log.info("scrcpy eşitleniyor: %s -> %s (v%s)", bundled, runtime, bv)
            shutil.rmtree(runtime, ignore_errors=True)
            shutil.copytree(bundled, runtime)
            with open(os.path.join(runtime, VERSION_FILE), "w", encoding="utf-8") as f:
                f.write(bv)
        except OSError as e:
            log.warning("scrcpy eşitlenemedi (%s), paketlenmiş sürüm kullanılacak", e)
            return bundled
    return runtime


def check_latest():
    """(sürüm, indirme_url, sha256) ya da None."""
    data = json.loads(fetch_text(LATEST_RELEASE_API, timeout=15))
    tag = (data.get("tag_name") or "").lstrip("v")
    for a in data.get("assets", []):
        name = a.get("name", "")
        if "win64" in name and name.endswith(".zip"):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1] if digest.startswith("sha256:") else None
            return tag, a.get("browser_download_url"), sha
    return None


def is_newer(latest: str, current: str) -> bool:
    return _vtuple(latest) > _vtuple(current)


def install_release(url: str, version: str, sha256: str = None, target_dir: str = None,
                    progress=None, cancel=None) -> str:
    """scrcpy zip'ini indirip target_dir (varsayılan runtime bin) içine atomik olarak kurar."""
    target_dir = target_dir or runtime_bin_dir()
    zip_path = os.path.join(temp_dir(), f"scrcpy-{version}.zip")
    download(url, zip_path, progress, cancel, ("sha256", sha256) if sha256 else None)
    staging = target_dir + "_new"
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging)
    with zipfile.ZipFile(zip_path) as zf:
        for m in zf.infolist():
            name = os.path.basename(m.filename)
            if m.is_dir() or not name:
                continue
            with zf.open(m) as s, open(os.path.join(staging, name), "wb") as t:
                shutil.copyfileobj(s, t)
    os.remove(zip_path)
    if not _valid(staging):
        shutil.rmtree(staging, ignore_errors=True)
        raise RuntimeError("İndirilen scrcpy paketi eksik")
    # icon.png gibi ek dosyaları koru
    if os.path.isdir(target_dir):
        for keep in ("icon.png",):
            src = os.path.join(target_dir, keep)
            if os.path.exists(src) and not os.path.exists(os.path.join(staging, keep)):
                shutil.copy2(src, staging)
    with open(os.path.join(staging, VERSION_FILE), "w", encoding="utf-8") as f:
        f.write(version)
    old = target_dir + "_old"
    shutil.rmtree(old, ignore_errors=True)
    if os.path.isdir(target_dir):
        os.rename(target_dir, old)
    os.rename(staging, target_dir)
    shutil.rmtree(old, ignore_errors=True)
    return target_dir


class ScrcpyEmbedder(QObject):
    """scrcpy'yi başlatır, penceresini bulur ve host widget içine gömer.

    mode="child": Win32 SetParent ile gerçek alt pencere (önerilen, titreme yok).
    mode="overlay": ayrı pencere ana pencereyi takip eder (uyumluluk modu).
    """

    embedded = pyqtSignal()
    failed = pyqtSignal(str)
    exited = pyqtSignal(int)

    def __init__(self, host_widget, owner_window, parent=None):
        super().__init__(parent)
        self.host = host_widget
        self.owner = owner_window
        self.bin_dir = ""
        self.proc = None
        self.hwnd = None
        self.mode = "child"
        self._log = None
        self._search_ticks = 0
        self._last_geom = None
        self._focus_inside = False

        self._search_timer = QTimer(self)
        self._search_timer.timeout.connect(self._search_window)
        self._watch_timer = QTimer(self)
        self._watch_timer.timeout.connect(self._watch)

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, serial: str, adb_path: str, mode: str = "child") -> None:
        self.stop()
        self.mode = mode
        exe = os.path.join(self.bin_dir, "scrcpy.exe")
        if not os.path.exists(exe):
            self.failed.emit(f"scrcpy.exe bulunamadı: {exe}")
            return
        x, y, w, h = win32.window_rect(int(self.host.winId()))
        cmd = [
            exe, "-s", serial, f"--window-title={WINDOW_TITLE}", "--window-borderless",
            f"--window-x={x}", f"--window-y={y}", f"--window-width={max(w, 50)}", f"--window-height={max(h, 50)}",
            "--max-size=1920", "--stay-awake", "--max-fps=60", "--no-audio",
        ]
        env = os.environ.copy()
        env["ADB"] = adb_path
        env["SCRCPY_SERVER_PATH"] = os.path.join(self.bin_dir, "scrcpy-server")
        self._log = open(os.path.join(logs_dir(), "scrcpy.log"), "w", encoding="utf-8", errors="replace")
        log.info("scrcpy başlatılıyor: %s", " ".join(cmd))
        try:
            self.proc = proc.popen(cmd, stdout=self._log, stderr=proc.subprocess.STDOUT, env=env, cwd=self.bin_dir)
        except OSError as e:
            self.failed.emit(str(e))
            return
        self._search_ticks = 0
        self._search_timer.start(100)

    def stop(self) -> None:
        self._search_timer.stop()
        self._watch_timer.stop()
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except proc.subprocess.TimeoutExpired:
                    self.proc.kill()
            self.proc = None
        self.hwnd = None
        self._last_geom = None
        if self._log:
            self._log.close()
            self._log = None

    def _search_window(self) -> None:
        self._search_ticks += 1
        if self.proc is None or self.proc.poll() is not None:
            self._search_timer.stop()
            code = self.proc.returncode if self.proc else -1
            self.failed.emit(f"scrcpy kapandı (kod {code}). Ayrıntı: logs\\scrcpy.log")
            self.proc = None
            return
        wins = win32.find_windows_by_pid(self.proc.pid, WINDOW_TITLE)
        if wins:
            self._search_timer.stop()
            self.hwnd = wins[0]
            self._attach()
            return
        if self._search_ticks > 200:  # 20 sn
            self._search_timer.stop()
            self.failed.emit("scrcpy penceresi bulunamadı")
            self.stop()

    def _attach(self) -> None:
        host_hwnd = int(self.host.winId())
        if self.mode == "child":
            w, h = win32.client_size(host_hwnd)
            if not win32.embed_as_child(self.hwnd, host_hwnd, w, h):
                log.warning("SetParent başarısız, overlay moduna geçiliyor")
                self.mode = "overlay"
        if self.mode == "overlay":
            win32.make_owned_tool_window(self.hwnd, int(self.owner.winId()))
        self.sync_geometry(force=True)
        self._watch_timer.start(50 if self.mode == "overlay" else 80)
        self.focus()
        self.embedded.emit()

    def sync_geometry(self, force: bool = False) -> None:
        if not win32.is_window(self.hwnd):
            return
        host_hwnd = int(self.host.winId())
        if self.mode == "child":
            w, h = win32.client_size(host_hwnd)
            geom = (0, 0, w, h)
            cur = win32.client_size(self.hwnd)
            if force or geom != self._last_geom or cur != (w, h):
                win32.move_window(self.hwnd, 0, 0, w, h)
                self._last_geom = geom
        else:
            visible = self.owner.isVisible() and not self.owner.isMinimized() and self.host.isVisible()
            if not visible:
                if self._last_geom != "hidden":
                    win32.show_window(self.hwnd, False)
                    self._last_geom = "hidden"
                return
            geom = win32.window_rect(host_hwnd)
            if force or geom != self._last_geom:
                if self._last_geom == "hidden" or force:
                    win32.show_window(self.hwnd, True)
                win32.move_window(self.hwnd, *geom)
                self._last_geom = geom

    def focus(self) -> None:
        if win32.is_window(self.hwnd):
            win32.set_focus(self.hwnd)

    def _watch(self) -> None:
        if self.proc is not None and self.proc.poll() is not None:
            code = self.proc.returncode
            self.stop()
            self.exited.emit(code)
            return
        self.sync_geometry()
        # Ekran alanına tıklandığında klavye odağını scrcpy'ye ver
        if self.mode == "child" and self.owner.isActiveWindow() and win32.is_window(self.hwnd):
            pressed = win32.mouse_button_down()
            if pressed and not self._focus_inside:
                cx, cy = win32.cursor_pos()
                x, y, w, h = win32.window_rect(int(self.host.winId()))
                if x <= cx < x + w and y <= cy < y + h:
                    self.focus()
            self._focus_inside = pressed
