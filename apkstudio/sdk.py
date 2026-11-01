"""Android SDK keşfi, ön koşul kontrolleri ve otomatik kurulum (JDK + cmdline-tools + AVD)."""

import logging
import os
import re
import shutil
import threading
import zipfile
import xml.etree.ElementTree as ET

from . import proc
from .downloader import Cancelled, check_cancel, download, fetch_text
from .i18n import T
from .paths import local_appdata

log = logging.getLogger(__name__)

JDK_URL = "https://aka.ms/download-jdk/microsoft-jdk-17.0.10-windows-x64.zip"
JDK_SHA_URL = JDK_URL + ".sha256sum.txt"
CMDLINE_TOOLS_FILE = "commandlinetools-win-11076708_latest.zip"
CMDLINE_TOOLS_URL = "https://dl.google.com/android/repository/" + CMDLINE_TOOLS_FILE
REPOSITORY_XML_URL = "https://dl.google.com/android/repository/repository2-3.xml"
LICENSE_URL = "https://developer.android.com/studio/terms"

API_LEVEL = "32"  # Android 12L - x86_64 imajında ARM çeviri katmanı bulunur
BUILD_TOOLS = "34.0.0"
AVD_NAME = "APK_Studio_ARM_Engine"
AVD_DEVICE = "pixel_5"
MIN_FREE_GB = 8
IMAGE_VARIANTS = {"google_apis": "Google APIs", "google_apis_playstore": "Google Play Store"}


class SdkError(Exception):
    pass


def system_image(variant: str) -> str:
    return f"system-images;android-{API_LEVEL};{variant};x86_64"


def avd_name_for(variant: str) -> str:
    return AVD_NAME if variant == "google_apis" else f"{AVD_NAME}_PlayStore"


def is_own_avd(name: str) -> bool:
    return bool(name) and name.startswith(AVD_NAME)


def find_sdk_root() -> str:
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        p = os.environ.get(var)
        if p and os.path.isdir(p):
            return p
    return os.path.join(local_appdata(), "Android", "Sdk")


def _version_key(name: str):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", name))


class Sdk:
    def __init__(self, root: str = None):
        self.root = root or find_sdk_root()
        self.portable_jdk_dir = os.path.join(os.path.dirname(self.root), "PortableJDK")

    # ---- yollar -------------------------------------------------------------
    @property
    def emulator_exe(self) -> str:
        return os.path.join(self.root, "emulator", "emulator.exe")

    @property
    def adb_exe(self) -> str:
        return os.path.join(self.root, "platform-tools", "adb.exe")

    def cmdline_bin(self):
        base = os.path.join(self.root, "cmdline-tools")
        candidates = [os.path.join(base, "latest", "bin")]
        if os.path.isdir(base):
            for d in sorted(os.listdir(base), key=_version_key, reverse=True):
                candidates.append(os.path.join(base, d, "bin"))
        for c in candidates:
            if os.path.exists(os.path.join(c, "sdkmanager.bat")):
                return c
        return None

    @property
    def avd_home(self) -> str:
        if os.environ.get("ANDROID_AVD_HOME"):
            return os.environ["ANDROID_AVD_HOME"]
        user_home = os.environ.get("ANDROID_USER_HOME") or os.path.join(os.path.expanduser("~"), ".android")
        return os.path.join(user_home, "avd")

    def has_emulator(self) -> bool:
        return os.path.exists(self.emulator_exe)

    # ---- sorgular -----------------------------------------------------------
    def list_avds(self) -> list:
        if not self.has_emulator():
            return []
        res = proc.run([self.emulator_exe, "-list-avds"], timeout=30)
        avds = []
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if line and " " not in line and not line.startswith(("INFO", "WARNING", "ERROR")):
                avds.append(line)
        return avds

    def find_aapt(self):
        bt = os.path.join(self.root, "build-tools")
        if not os.path.isdir(bt):
            return None
        for ver in sorted(os.listdir(bt), key=_version_key, reverse=True):
            for exe in ("aapt2.exe", "aapt.exe"):
                p = os.path.join(bt, ver, exe)
                if os.path.exists(p):
                    return p
        return None

    def accel_check(self):
        """(ok, açıklama). Donanım hızlandırma (WHPX/AEHD/HAXM) var mı?"""
        if not self.has_emulator():
            return True, ""
        res = proc.run([self.emulator_exe, "-accel-check"], timeout=60)
        text = ((res.stdout or "") + (res.stderr or "")).strip()
        return res.returncode == 0, text

    def free_space_gb(self) -> float:
        path = self.root
        while path and not os.path.exists(path):
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        try:
            return shutil.disk_usage(path).free / (1024 ** 3)
        except OSError:
            return 999.0

    def find_java_home(self):
        def ok(home):
            return home and os.path.exists(os.path.join(home, "bin", "java.exe"))

        candidates = [os.environ.get("JAVA_HOME")]
        for pf in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
            candidates.append(os.path.join(pf, "Android", "Android Studio", "jbr"))
        if os.path.isdir(self.portable_jdk_dir):
            for item in os.listdir(self.portable_jdk_dir):
                candidates.append(os.path.join(self.portable_jdk_dir, item))
        for c in candidates:
            if ok(c):
                return c
        return None

    # ---- AVD config -----------------------------------------------------------
    def avd_config_path(self, name: str) -> str:
        return os.path.join(self.avd_home, f"{name}.avd", "config.ini")

    def patch_avd_config(self, name: str, overrides: dict) -> bool:
        """Sadece APK Studio'nun kendi AVD'lerinde çağrılmalı. İlk seferde yedek alır."""
        path = self.avd_config_path(name)
        if not os.path.exists(path):
            log.warning("AVD config bulunamadı: %s", path)
            return False
        backup = path + ".apkstudio.bak"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        seen, out = set(), []
        for line in lines:
            key = line.split("=", 1)[0].strip() if "=" in line else None
            if key in overrides:
                out.append(f"{key}={overrides[key]}\n")
                seen.add(key)
            else:
                out.append(line)
        for k, v in overrides.items():
            if k not in seen:
                out.append(f"{k}={v}\n")
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)
        return True


class SdkInstaller:
    """İlk kurulum. status(str), progress(done, total) geri çağrıları; cancel=threading.Event."""

    def __init__(self, sdk: Sdk, status=None, progress=None, cancel: threading.Event = None):
        self.sdk = sdk
        self.status = status or (lambda s: log.info(s))
        self.progress = progress or (lambda d, t: None)
        self.cancel = cancel or threading.Event()

    # ---- adımlar --------------------------------------------------------------
    def check_disk(self, needed_gb: float = MIN_FREE_GB) -> None:
        free = self.sdk.free_space_gb()
        if free < needed_gb:
            raise SdkError(T(f"Yetersiz disk alanı: {free:.1f} GB boş, en az {needed_gb} GB gerekli ({self.sdk.root}).",
                             f"Not enough disk space: {free:.1f} GB free, at least {needed_gb} GB required ({self.sdk.root})."))

    def ensure_jdk(self) -> str:
        home = self.sdk.find_java_home()
        if home:
            log.info("Java bulundu: %s", home)
            return home
        self.status(T("Taşınabilir Java 17 indiriliyor...", "Downloading portable Java 17..."))
        os.makedirs(self.sdk.portable_jdk_dir, exist_ok=True)
        expected = None
        try:
            expected = ("sha256", fetch_text(JDK_SHA_URL).split()[0])
        except Exception as e:  # noqa: BLE001
            log.warning("JDK sha256 alınamadı: %s", e)
        zip_path = os.path.join(self.sdk.portable_jdk_dir, "jdk.zip")
        download(JDK_URL, zip_path, self.progress, self.cancel, expected)
        self.status(T("Java arşivden çıkarılıyor...", "Extracting Java..."))
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(self.sdk.portable_jdk_dir)
        os.remove(zip_path)
        home = self.sdk.find_java_home()
        if not home:
            raise SdkError(T("Java kurulumu doğrulanamadı.", "Java installation could not be verified."))
        return home

    def _cmdline_tools_sha1(self):
        try:
            root = ET.fromstring(fetch_text(REPOSITORY_XML_URL, timeout=30))
            for el in root.iter():
                if el.tag.split("}")[-1] != "complete":
                    continue
                url = el.find("url")
                chk = el.find("checksum")
                if url is not None and chk is not None and url.text and url.text.strip() == CMDLINE_TOOLS_FILE:
                    return (chk.get("type") or "sha1"), chk.text.strip()
        except Exception as e:  # noqa: BLE001
            log.warning("cmdline-tools hash bilgisi alınamadı: %s", e)
        return None

    def ensure_cmdline_tools(self) -> str:
        existing = self.sdk.cmdline_bin()
        if existing:
            return existing
        self.status(T("Android SDK komut satırı araçları indiriliyor...", "Downloading Android SDK command-line tools..."))
        base = os.path.join(self.sdk.root, "cmdline-tools")
        os.makedirs(base, exist_ok=True)
        zip_path = os.path.join(self.sdk.root, "cmdline-tools.zip")
        download(CMDLINE_TOOLS_URL, zip_path, self.progress, self.cancel, self._cmdline_tools_sha1())
        temp = os.path.join(base, "_temp")
        shutil.rmtree(temp, ignore_errors=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(temp)
        os.remove(zip_path)
        latest = os.path.join(base, "latest")
        shutil.rmtree(latest, ignore_errors=True)
        shutil.move(os.path.join(temp, "cmdline-tools"), latest)
        shutil.rmtree(temp, ignore_errors=True)
        b = self.sdk.cmdline_bin()
        if not b:
            raise SdkError(T("sdkmanager kurulamadı.", "sdkmanager could not be installed."))
        return b

    def env(self, java_home: str, cmd_bin: str) -> dict:
        env = os.environ.copy()
        env["JAVA_HOME"] = java_home
        env["ANDROID_SDK_ROOT"] = self.sdk.root
        env["ANDROID_HOME"] = self.sdk.root
        env["PATH"] = os.pathsep.join([os.path.join(java_home, "bin"), cmd_bin, env.get("PATH", "")])
        return env

    def run_streaming(self, cmd: list, env: dict, answers: str = None, label: str = "") -> int:
        """sdkmanager çıktısını satır satır okuyup yüzde ilerlemesini yansıtır."""
        log.info("Çalıştırılıyor: %s", " ".join(cmd))
        p = proc.popen(cmd, stdin=proc.subprocess.PIPE, stdout=proc.subprocess.PIPE,
                       stderr=proc.subprocess.STDOUT, env=env)
        try:
            if answers:
                p.stdin.write(answers.encode("utf-8"))
            p.stdin.close()
        except OSError:
            pass
        buf = b""
        while True:
            if self.cancel.is_set():
                p.kill()
                raise Cancelled()
            ch = p.stdout.read(1)
            if not ch:
                break
            if ch in (b"\r", b"\n"):
                line = buf.decode("utf-8", errors="replace").strip()
                buf = b""
                if not line:
                    continue
                m = re.search(r"(\d{1,3})%", line)
                if m:
                    self.progress(int(m.group(1)), 100)
                    if label:
                        self.status(f"{label} — {line[-90:]}")
                else:
                    log.info("[sdk] %s", line)
            else:
                buf += ch
        return p.wait()

    def install(self, variant: str = "google_apis", ram_mb: int = 4096, cores: int = 4) -> str:
        avd = avd_name_for(variant)
        image = system_image(variant)
        image_dir = os.path.join(self.sdk.root, "system-images", f"android-{API_LEVEL}", variant, "x86_64")
        if not os.path.isdir(image_dir):
            self.check_disk()
        check_cancel(self.cancel)

        java_home = self.ensure_jdk()
        check_cancel(self.cancel)
        cmd_bin = self.ensure_cmdline_tools()
        env = self.env(java_home, cmd_bin)
        sdkmanager = os.path.join(cmd_bin, "sdkmanager.bat")
        avdmanager = os.path.join(cmd_bin, "avdmanager.bat")

        self.status(T("SDK lisansları onaylanıyor...", "Accepting SDK licenses..."))
        self.run_streaming([sdkmanager, f"--sdk_root={self.sdk.root}", "--licenses"], env, "y\n" * 60)

        label = T("Android motoru indiriliyor (~1.5 GB)", "Downloading Android engine (~1.5 GB)")
        self.status(label + "...")
        pkgs = ["platform-tools", "emulator", f"platforms;android-{API_LEVEL}", f"build-tools;{BUILD_TOOLS}", image]
        rc = self.run_streaming([sdkmanager, f"--sdk_root={self.sdk.root}"] + pkgs, env, "y\n" * 20, label)
        if rc != 0 or not self.sdk.has_emulator() or not os.path.isdir(image_dir):
            raise SdkError(T(f"SDK paketleri kurulamadı (kod {rc}). Ayrıntılar log dosyasında.",
                             f"SDK packages could not be installed (code {rc}). See log file."))

        self.status(T(f"Sanal cihaz oluşturuluyor: {avd}", f"Creating virtual device: {avd}"))
        res = proc.run([avdmanager, "create", "avd", "-n", avd, "-k", image, "-d", AVD_DEVICE, "--force"],
                       timeout=180, env=env, input="no\n")
        log.info("avdmanager: rc=%s %s %s", res.returncode, res.stdout, res.stderr)
        if avd not in self.sdk.list_avds():
            raise SdkError(T(f"AVD oluşturulamadı: {res.stderr or res.stdout}", f"AVD creation failed: {res.stderr or res.stdout}"))

        self.sdk.patch_avd_config(avd, {
            "hw.ramSize": str(ram_mb), "hw.cpu.ncore": str(cores), "hw.gpu.enabled": "yes",
            "hw.keyboard": "yes", "hw.mainKeys": "no", "disk.dataPartition.size": "8G",
            "fastboot.forceColdBoot": "no",
        })
        self.status(T("Kurulum tamamlandı.", "Installation complete."))
        return avd

    def update_packages(self) -> int:
        java_home = self.ensure_jdk()
        cmd_bin = self.ensure_cmdline_tools()
        env = self.env(java_home, cmd_bin)
        sdkmanager = os.path.join(cmd_bin, "sdkmanager.bat")
        label = T("SDK paketleri güncelleniyor", "Updating SDK packages")
        self.status(label + "...")
        rc = self.run_streaming([sdkmanager, f"--sdk_root={self.sdk.root}", "--update"], env, "y\n" * 20, label)
        if rc != 0:
            raise SdkError(T(f"Güncelleme başarısız (kod {rc}).", f"Update failed (code {rc})."))
        return rc
