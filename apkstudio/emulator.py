"""Android Emulator süreç yönetimi: başlatma, açılışı bekleme, düzgün kapatma."""

import logging
import os
import threading
import time
from dataclasses import dataclass

from . import proc
from .adb import Adb
from .downloader import check_cancel
from .i18n import T
from .paths import logs_dir
from .sdk import Sdk

log = logging.getLogger(__name__)


class EngineError(Exception):
    pass


@dataclass
class EngineOptions:
    avd: str
    port: int
    camera: str = "webcam0"
    gpu: str = "auto"
    quick_boot: bool = True
    boot_timeout: int = 300


class EmulatorController:
    def __init__(self, sdk: Sdk, adb: Adb):
        self.sdk = sdk
        self.adb = adb
        self.proc = None
        self._log_handle = None
        self._accel_checked = False

    @property
    def started_by_us(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def check_acceleration(self) -> None:
        if self._accel_checked:
            return
        ok, text = self.sdk.accel_check()
        log.info("accel-check: ok=%s %s", ok, text)
        if not ok:
            raise EngineError(T(
                "Donanım hızlandırma kullanılamıyor. Windows Özellikleri'nden 'Windows Hiper Yönetici Platformu'nu "
                "(Windows Hypervisor Platform) etkinleştirip bilgisayarı yeniden başlatın ve BIOS'ta sanallaştırmanın "
                f"(VT-x / AMD-V) açık olduğundan emin olun.\n\nAyrıntı: {text[-400:]}",
                "Hardware acceleration is unavailable. Enable 'Windows Hypervisor Platform' in Windows Features, "
                "reboot, and make sure virtualization (VT-x / AMD-V) is enabled in BIOS.\n\n"
                f"Details: {text[-400:]}"))
        self._accel_checked = True

    def start(self, opts: EngineOptions) -> None:
        if not self.sdk.has_emulator():
            raise EngineError(T("emulator.exe bulunamadı. Lütfen Android motorunu kurun.",
                                "emulator.exe not found. Please install the Android engine."))
        # Ön ve arka kameraları daima tanımlı tutarak kamera sayısı 0 hatasını önle
        cam_back = opts.camera if opts.camera != "none" else "none"
        cam_front = "emulated" if opts.camera != "none" else "none"
        if cam_back == "none":
            cam_front = "none"

        cmd = [
            self.sdk.emulator_exe, "-avd", opts.avd, "-port", str(opts.port), "-no-window", "-no-boot-anim",
            "-gpu", opts.gpu, "-camera-back", cam_back, "-camera-front", cam_front,
        ]
        if not opts.quick_boot:
            cmd.append("-no-snapshot-load")
        log.info("Emulator başlatılıyor: %s", " ".join(cmd))
        self._close_log()
        self._log_handle = open(os.path.join(logs_dir(), "emulator.log"), "w", encoding="utf-8", errors="replace")
        env = os.environ.copy()
        env["ANDROID_SDK_ROOT"] = self.sdk.root
        env["ANDROID_HOME"] = self.sdk.root
        self.proc = proc.popen(cmd, stdout=self._log_handle, stderr=proc.subprocess.STDOUT, env=env)

    def wait_boot(self, timeout: int, cancel: threading.Event = None, on_tick=None) -> None:
        start = time.monotonic()
        while True:
            check_cancel(cancel)
            elapsed = time.monotonic() - start
            if self.proc is not None and self.proc.poll() is not None:
                raise EngineError(T(
                    f"Emülatör beklenmedik şekilde kapandı (kod {self.proc.returncode}). Ayrıntı: logs\\emulator.log",
                    f"Emulator exited unexpectedly (code {self.proc.returncode}). See logs\\emulator.log"))
            if self.adb.is_online() and self.adb.is_booted():
                log.info("Emulator %.0f sn'de açıldı", elapsed)
                return
            if elapsed > timeout:
                raise EngineError(T(
                    f"Android motoru {timeout} sn içinde açılamadı. Ayarlardan süreyi artırabilir veya GPU modunu "
                    "'Yazılımsal' yapabilirsiniz.",
                    f"Android engine did not boot within {timeout}s. Increase the timeout in settings or switch "
                    "GPU mode to 'Software'."))
            if on_tick:
                on_tick(int(elapsed), timeout)
            time.sleep(1.5)

    def stop(self, wait: float = 15) -> None:
        """'adb emu kill' ile düzgün kapatır (Quick Boot anlık görüntüsü kaydedilir)."""
        if self.adb.is_online():
            self.adb.kill_emulator()
        if self.proc is not None:
            try:
                self.proc.wait(timeout=wait)
            except proc.subprocess.TimeoutExpired:
                log.warning("Emulator kapanmadı, sonlandırılıyor")
                self.proc.kill()
            self.proc = None
        else:
            end = time.monotonic() + wait
            while time.monotonic() < end and self.adb.serial in self.adb.devices():
                time.sleep(0.5)
        self._close_log()

    def _close_log(self) -> None:
        if self._log_handle:
            try:
                self._log_handle.close()
            except OSError:
                pass
            self._log_handle = None
