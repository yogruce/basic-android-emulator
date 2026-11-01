"""Tek bir cihaz seri numarasına bağlı, zaman aşımlı ADB istemcisi."""

import logging
import os
import re
import subprocess

from . import proc

log = logging.getLogger(__name__)


class Adb:
    def __init__(self, adb_path: str, serial: str):
        self.adb_path = adb_path
        self.serial = serial

    # ---- temel ------------------------------------------------------------
    def raw(self, args, timeout: float = 30, text: bool = True) -> subprocess.CompletedProcess:
        return proc.run([self.adb_path] + list(args), timeout=timeout, text=text)

    def run(self, args, timeout: float = 30, text: bool = True) -> subprocess.CompletedProcess:
        return self.raw(["-s", self.serial] + list(args), timeout=timeout, text=text)

    def shell(self, *args, timeout: float = 30) -> subprocess.CompletedProcess:
        return self.run(["shell"] + list(args), timeout=timeout)

    def fire(self, args) -> None:
        """Sonucu beklenmeyen hızlı komutlar (navigasyon tuşları vb.)."""
        try:
            proc.popen([self.adb_path, "-s", self.serial] + list(args),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            log.error("adb çalıştırılamadı: %s", e)

    def start_server(self) -> None:
        self.raw(["start-server"], timeout=30)

    def devices(self) -> dict:
        res = self.raw(["devices"], timeout=10)
        out = {}
        for line in (res.stdout or "").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2:
                out[parts[0].strip()] = parts[1].strip()
        return out

    def is_online(self) -> bool:
        return self.devices().get(self.serial) == "device"

    def getprop(self, name: str, timeout: float = 8) -> str:
        return (self.shell("getprop", name, timeout=timeout).stdout or "").strip()

    def is_booted(self) -> bool:
        return self.getprop("sys.boot_completed") == "1"

    # ---- uygulamalar --------------------------------------------------------
    def install(self, apks: list, timeout: float = 600):
        """(başarılı_mı, mesaj). Birden fazla dosya -> install-multiple (split APK)."""
        if len(apks) == 1:
            args = ["install", "-r", "-g", "-t", apks[0]]
        else:
            args = ["install-multiple", "-r", "-g", "-t"] + list(apks)
        res = self.run(args, timeout=timeout)
        out = ((res.stdout or "") + "\n" + (res.stderr or "")).strip()
        ok = res.returncode == 0 and "Success" in out
        if not ok:
            log.error("Kurulum hatası: %s", out)
        return ok, out

    def list_packages(self, third_party: bool = True) -> list:
        args = ["pm", "list", "packages"] + (["-3"] if third_party else [])
        res = self.shell(*args, timeout=20)
        return sorted(l.replace("package:", "").strip() for l in (res.stdout or "").splitlines() if l.startswith("package:"))

    def resolve_launcher(self, pkg: str):
        res = self.shell("cmd", "package", "resolve-activity", "--brief",
                         "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", pkg, timeout=15)
        for line in reversed((res.stdout or "").splitlines()):
            line = line.strip()
            if "/" in line and line.startswith(pkg):
                return line
        return None

    def launch(self, pkg: str) -> bool:
        comp = self.resolve_launcher(pkg)
        if comp:
            res = self.shell("am", "start", "-n", comp, timeout=20)
            if res.returncode == 0 and "Error" not in (res.stdout or ""):
                return True
        res = self.shell("monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1", timeout=20)
        return res.returncode == 0 and "No activities found" not in (res.stdout or "")

    def force_stop(self, pkg: str) -> None:
        self.shell("am", "force-stop", pkg)

    def clear_data(self, pkg: str) -> bool:
        return "Success" in (self.shell("pm", "clear", pkg).stdout or "")

    def uninstall(self, pkg: str) -> bool:
        return "Success" in (self.run(["uninstall", pkg], timeout=60).stdout or "")

    def pidof(self, pkg: str) -> str:
        out = (self.shell("pidof", pkg, timeout=8).stdout or "").strip()
        return out.split()[0] if out else ""

    def set_appop_camera(self, pkg: str, allow: bool) -> None:
        self.shell("cmd", "appops", "set", pkg, "CAMERA", "allow" if allow else "ignore")

    def set_camera_privacy(self, blocked: bool) -> None:
        self.shell("cmd", "sensor_privacy", "enable" if blocked else "disable", "0", "camera")

    # ---- ekran ------------------------------------------------------------
    def wake_and_unlock(self) -> None:
        self.shell("input", "keyevent", "224")
        self.shell("wm", "dismiss-keyguard")

    def set_display(self, res: str, dpi: str) -> None:
        self.shell("wm", "size", res)
        self.shell("wm", "density", dpi)

    def reset_display(self) -> None:
        self.shell("wm", "size", "reset")
        self.shell("wm", "density", "reset")
        self.set_rotation(0)

    def set_rotation(self, rotation: int) -> None:
        self.shell("settings", "put", "system", "accelerometer_rotation", "0")
        self.shell("settings", "put", "system", "user_rotation", str(rotation))

    def screencap(self, dest: str) -> bool:
        res = self.run(["exec-out", "screencap", "-p"], timeout=30, text=False)
        data = res.stdout or b""
        if res.returncode != 0 or not data.startswith(b"\x89PNG"):
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True

    def push(self, src: str, dst_dir: str = "/sdcard/Download/") -> bool:
        res = self.run(["push", src, dst_dir.rstrip("/") + "/" + os.path.basename(src)], timeout=600)
        return res.returncode == 0

    def pull(self, src: str, dst: str) -> bool:
        return self.run(["pull", src, dst], timeout=300).returncode == 0

    # ---- emulator konsolu ------------------------------------------------------
    def emu(self, *args, timeout: float = 15) -> subprocess.CompletedProcess:
        return self.run(["emu"] + list(args), timeout=timeout)

    def geo_fix(self, lat: float, lon: float) -> None:
        self.emu("geo", "fix", f"{lon:.6f}", f"{lat:.6f}")  # sıra: boylam, enlem

    def network(self, speed: str, delay: str) -> None:
        self.emu("network", "speed", speed)
        self.emu("network", "delay", delay)

    def battery(self, level: int, charging: bool) -> None:
        self.emu("power", "capacity", str(int(level)))
        self.emu("power", "ac", "on" if charging else "off")
        self.emu("power", "status", "charging" if charging else "discharging")

    def kill_emulator(self) -> None:
        self.emu("kill", timeout=10)

    @staticmethod
    def parse_version(text: str) -> str:
        m = re.search(r"Version\s+([\d.]+)", text or "")
        return m.group(1) if m else ""
