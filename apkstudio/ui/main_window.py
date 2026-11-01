"""APK Studio Player - Modernleştirilmiş ve Modüler Ana Pencere."""

import os
import sys
import time
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox,
    QProgressBar, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QPoint

from .. import APP_TITLE, __version__
from ..i18n import T
from ..constants import (
    DEVICE_SERIAL, EMULATOR_PORT, device_profiles, camera_modes,
    APK_EXTENSIONS
)
from ..paths import media_dir, icon_path
from ..settings import Settings
from ..sdk import Sdk, is_own_avd
from ..adb import Adb
from ..emulator import EmulatorController, EngineOptions
from ..scrcpy import ScrcpyEmbedder, ensure_runtime_bin
from ..apk import prepare_bundle, ApkError
from ..jobs import JobQueue

from .theme import get_stylesheet
from .settings_dialog import SettingsDialog
from .apps_dialog import AppsDialog
from .simulation_dialog import SimulationDialog
from .setup_wizard import SetupWizardDialog
from .logcat_view import LogcatWidget

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings

        # Çekirdek Servisler
        self.sdk = Sdk()
        self.runtime_bin = ensure_runtime_bin()

        # Tek bir ADB istemcisi
        adb_binary = self.sdk.adb_exe if os.path.exists(self.sdk.adb_exe) else os.path.join(self.runtime_bin, "adb.exe")
        self.adb = Adb(adb_binary, DEVICE_SERIAL)

        self.emulator = EmulatorController(self.sdk, self.adb)
        self.job_queue = JobQueue(self)

        self.landscape = self.settings.get("landscape")
        self.camera_live = self.settings.get("camera_enabled")
        self.last_installed_pkg = self.settings.get("last_pkg")

        self.init_ui()
        self.apply_theme()

        # Scrcpy Entegrasyonu
        self.scrcpy = ScrcpyEmbedder(self.screen_slot, self, self)
        self.scrcpy.bin_dir = self.runtime_bin
        self.scrcpy.embedded.connect(self.on_scrcpy_embedded)
        self.scrcpy.failed.connect(self.on_scrcpy_failed)
        self.scrcpy.exited.connect(self.on_scrcpy_exited)

        # JobQueue Sinyalleri
        self.job_queue.status.connect(self.set_status)
        self.job_queue.progress.connect(self.on_job_progress)
        self.job_queue.busy_changed.connect(self.on_job_busy_changed)
        self.job_queue.error.connect(lambda name, err: self.show_error(err))

        # Açılış Otomatik Kontrolü
        QTimer.singleShot(700, self.auto_check_state)

    def init_ui(self):
        self.setWindowTitle(f"{APP_TITLE} v{__version__}")
        self.resize(1340, 880)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # SOL KONTROL PANELİ
        # -------------------------------------------------------------
        left_panel = QFrame()
        left_panel.setObjectName("panelFrame")
        left_panel.setFixedWidth(340)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(9)

        # Başlık ve Ayarlar Butonu
        title_row = QHBoxLayout()
        title_lbl = QLabel("APK STUDIO ENGINE")
        title_lbl.setObjectName("titleLabel")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        btn_settings = QPushButton("⚙")
        btn_settings.setFixedSize(32, 32)
        btn_settings.setToolTip(T("Ayarlar", "Settings"))
        btn_settings.clicked.connect(self.open_settings)
        title_row.addWidget(btn_settings)
        left_layout.addLayout(title_row)

        # Cihaz & Boyut Seçimi
        left_layout.addWidget(QLabel(T("📱 Cihaz Boyutu / Oranı:", "📱 Device Profile / Ratio:")))
        self.profile_combo = QComboBox()
        self.profiles_data = device_profiles()
        for name in self.profiles_data.keys():
            self.profile_combo.addItem(name)
        self.profile_combo.currentIndexChanged.connect(self.apply_device_profile)
        left_layout.addWidget(self.profile_combo)

        # Döndürme Butonu
        self.btn_rotate = QPushButton(T("🔄 Ekranı Döndür (Yatay / Dikey)", "🔄 Rotate Screen (Landscape / Portrait)"))
        self.btn_rotate.clicked.connect(self.toggle_rotation)
        left_layout.addWidget(self.btn_rotate)

        # Kamera Donanım Kaynağı
        cam_lbl = QLabel(T("📷 Kamera Kaynağı (Donanım):", "📷 Camera Source (Hardware):"))
        left_layout.addWidget(cam_lbl)

        self.camera_combo = QComboBox()
        for k, v in camera_modes().items():
            self.camera_combo.addItem(v, k)
        idx_cam = self.camera_combo.findData(self.settings.get("camera"))
        if idx_cam >= 0:
            self.camera_combo.setCurrentIndex(idx_cam)
        left_layout.addWidget(self.camera_combo)

        # Canlı Kamera Toggle
        self.btn_cam_toggle = QPushButton()
        self.update_cam_toggle_button()
        self.btn_cam_toggle.clicked.connect(self.toggle_camera_privacy)
        left_layout.addWidget(self.btn_cam_toggle)

        # Motor Başlat Butonu
        self.btn_start = QPushButton(T("🚀 Motoru Başlat / Ekranı Getir", "🚀 Start Engine / Show Screen"))
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.clicked.connect(lambda: self.start_engine_flow())
        left_layout.addWidget(self.btn_start)

        # APK Seç & Başlat
        btn_apk = QPushButton(T("📦 APK Seç, Kur ve Başlat", "📦 Select, Install & Run APK"))
        btn_apk.setObjectName("accentBtn")
        btn_apk.clicked.connect(self.open_apk_dialog)
        left_layout.addWidget(btn_apk)

        # Sürükle Bırak Alanı
        drop_box = QLabel(T(
            "⚡ SÜRÜKLE VE BIRAK ⚡\n\n.APK, .XAPK veya .APKS dosyasını\nburaya veya pencereye bırakın.",
            "⚡ DRAG & DROP ⚡\n\nDrop .APK, .XAPK or .APKS\nfile here or onto the window."
        ))
        drop_box.setAlignment(Qt.AlignCenter)
        drop_box.setStyleSheet(
            "border: 2px dashed #00E5FF; padding: 12px; color: #8B949E; border-radius: 8px; background-color: #0D1117;"
        )
        left_layout.addWidget(drop_box)

        # Ekstra Araçlar (Uygulamalar & Simülasyon)
        tools_row = QHBoxLayout()
        btn_apps = QPushButton(T("📱 Uygulamalar", "📱 Apps"))
        btn_apps.clicked.connect(self.open_apps_dialog)
        tools_row.addWidget(btn_apps)

        btn_sim = QPushButton(T("🌐 Simülasyon", "🌐 Simulation"))
        btn_sim.clicked.connect(self.open_simulation_dialog)
        tools_row.addWidget(btn_sim)
        left_layout.addLayout(tools_row)

        # Durum ve İlerleme Alanı
        self.status_lbl = QLabel(T("Durum: Hazır.", "Status: Ready."))
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet(
            "color: #FFD54F; font-size: 12px; padding: 6px; background: #0D1117; border-radius: 4px; border: 1px solid #21262D;"
        )
        left_layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # -------------------------------------------------------------
        # SAĞ EKRAN VE GÖRÜNTÜLEME ALANI
        # -------------------------------------------------------------
        right_panel = QFrame()
        right_panel.setObjectName("viewportFrame")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        # Dikey Splitter: Üstte Android Ekranı, Altta Logcat
        self.splitter = QSplitter(Qt.Vertical)

        # Ekran Alanı Container
        self.viewport_container = QWidget()
        vp_layout = QVBoxLayout(self.viewport_container)
        vp_layout.setContentsMargins(0, 0, 0, 0)
        vp_layout.setAlignment(Qt.AlignCenter)

        self.screen_slot = QFrame()
        self.screen_slot.setObjectName("screenSlot")
        self.screen_slot.setFixedSize(390, 845)
        slot_layout = QVBoxLayout(self.screen_slot)
        self.placeholder_lbl = QLabel(T("Android Ekranı Hazır Olduğunda Buraya Gelecek", "Android Screen Will Dock Here When Ready"))
        self.placeholder_lbl.setAlignment(Qt.AlignCenter)
        self.placeholder_lbl.setStyleSheet("color: #6E7681; font-weight: bold; font-size: 13px;")
        slot_layout.addWidget(self.placeholder_lbl)

        vp_layout.addWidget(self.screen_slot, alignment=Qt.AlignCenter)
        self.splitter.addWidget(self.viewport_container)

        # Logcat Alanı
        self.logcat_widget = LogcatWidget(self.adb)
        self.splitter.addWidget(self.logcat_widget)
        if not self.settings.get("logcat_visible"):
            self.logcat_widget.hide()

        right_layout.addWidget(self.splitter, stretch=1)

        # Alt Navigasyon & Kontrol Çubuğu
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(10)
        nav_bar.setAlignment(Qt.AlignCenter)

        btn_back = QPushButton(T("◀ Geri (Back)", "◀ Back"))
        btn_back.clicked.connect(lambda: self.adb.fire(["shell", "input", "keyevent", "4"]))
        nav_bar.addWidget(btn_back)

        btn_home = QPushButton(T("⏺ Ana Ekran (Home)", "⏺ Home"))
        btn_home.clicked.connect(lambda: self.adb.fire(["shell", "input", "keyevent", "3"]))
        nav_bar.addWidget(btn_home)

        btn_recent = QPushButton(T("⬛ Son Uygulamalar", "⬛ Recents"))
        btn_recent.clicked.connect(lambda: self.adb.fire(["shell", "input", "keyevent", "187"]))
        nav_bar.addWidget(btn_recent)

        btn_relaunch = QPushButton(T("▶️ Son APK'yı Aç", "▶️ Relaunch Last APK"))
        btn_relaunch.setObjectName("primaryBtn")
        btn_relaunch.clicked.connect(self.relaunch_last_apk)
        nav_bar.addWidget(btn_relaunch)

        btn_shot = QPushButton(T("📸 Ekran Görüntüsü", "📸 Screenshot"))
        btn_shot.clicked.connect(self.take_screenshot)
        nav_bar.addWidget(btn_shot)

        self.btn_toggle_logcat = QPushButton(T("📋 Logcat", "📋 Logcat"))
        self.btn_toggle_logcat.clicked.connect(self.toggle_logcat)
        nav_bar.addWidget(self.btn_toggle_logcat)

        right_layout.addLayout(nav_bar)
        main_layout.addWidget(right_panel, stretch=1)

    def apply_theme(self):
        theme = self.settings.get("theme")
        self.setStyleSheet(get_stylesheet(theme))

    def set_status(self, text: str):
        self.status_lbl.setText(text)

    def show_error(self, message: str):
        self.status_lbl.setText(T(f"❌ Hata: {message}", f"❌ Error: {message}"))
        QMessageBox.warning(self, T("Hata", "Error"), str(message))

    def on_job_progress(self, done: int, total: int):
        if total > 0:
            self.progress_bar.show()
            val = int(done * 100 / total)
            self.progress_bar.setValue(min(val, 100))
        else:
            self.progress_bar.hide()

    def on_job_busy_changed(self, busy: bool):
        self.btn_start.setEnabled(not busy)
        if not busy:
            self.progress_bar.hide()

    # -------------------------------------------------------------
    # İŞ AKIŞLARI (BAŞLATMA, DOCKING, KURULUM)
    # -------------------------------------------------------------
    def auto_check_state(self):
        if self.adb.is_online():
            self.set_status(T("Açık emülatör tespit edildi, ekran bağlanıyor...", "Running emulator detected, connecting..."))
            self.dock_screen()

    def get_target_avd(self) -> str:
        saved = self.settings.get("avd")
        avds = self.sdk.list_avds()
        if saved and saved in avds:
            return saved
        # Kendi AVD'miz varsa onu seç
        for a in avds:
            if is_own_avd(a):
                return a
        return avds[0] if avds else ""

    def start_engine_flow(self, apk_bundle=None):
        if self.job_queue.busy:
            return

        def _worker(job):
            # 1. Emülatör açık değilse başlat
            if not self.adb.is_online():
                avd = self.get_target_avd()
                if not avd:
                    raise RuntimeError("__NEEDS_SETUP__")

                # Donanım hızlandırma kontrolü
                self.emulator.check_acceleration()

                cam = self.camera_combo.currentData() if self.camera_live else "none"
                gpu = self.settings.get("gpu")
                quick = self.settings.get("quick_boot")
                timeout = self.settings.get("boot_timeout")

                opts = EngineOptions(avd=avd, port=EMULATOR_PORT, camera=cam, gpu=gpu, quick_boot=quick, boot_timeout=timeout)

                job.emit_status(T(f"'{avd}' sanal cihazı başlatılıyor...", f"Starting '{avd}' virtual device..."))
                self.emulator.start(opts)

                def _on_tick(elapsed, total):
                    job.emit_status(T(f"Sistem açılıyor ({elapsed}/{total} sn)...", f"Booting system ({elapsed}/{total}s)..."))

                self.emulator.wait_boot(timeout, cancel=job.cancel_event, on_tick=_on_tick)

            # Ekran kilidini aç
            job.emit_status(T("Ekran uyandırılıyor...", "Waking up device..."))
            self.adb.wake_and_unlock()

            # APK Kurulumu varsa yap
            if apk_bundle:
                job.emit_status(T(f"Kuruluyor: {apk_bundle.package or os.path.basename(apk_bundle.source)}...",
                                  f"Installing: {apk_bundle.package or os.path.basename(apk_bundle.source)}..."))
                ok, msg = self.adb.install(apk_bundle.apks)
                if not ok:
                    raise RuntimeError(T(f"Kurulum hatası: {msg}", f"Install error: {msg}"))

                # OBB dosyalarını aktar
                for local_obb, remote_obb in apk_bundle.obb:
                    job.emit_status(T("OBB veri dosyası aktarılıyor...", "Pushing OBB data file..."))
                    self.adb.shell("mkdir", "-p", os.path.dirname(remote_obb))
                    self.adb.push(local_obb, remote_obb)

                if apk_bundle.package:
                    self.last_installed_pkg = apk_bundle.package
                    self.settings.set("last_pkg", apk_bundle.package)
                    if not self.camera_live:
                        self.adb.set_appop_camera(apk_bundle.package, False)
                    job.emit_status(T(f"Başlatılıyor: {apk_bundle.package}...", f"Launching: {apk_bundle.package}..."))
                    self.adb.launch(apk_bundle.package)

            return apk_bundle

        def _on_success(bundle):
            if bundle:
                bundle.cleanup()
                name = bundle.package or os.path.basename(bundle.source)
                self.set_status(T(f"✅ Başlatıldı: {name}", f"✅ Launched: {name}"))
            else:
                self.set_status(T("✅ Motor ve Ekran Aktif!", "✅ Engine & Screen Active!"))

            # Scrcpy'yi panele bağla
            self.dock_screen()

        def _on_error(err):
            if str(err) == "__NEEDS_SETUP__":
                self.open_setup_wizard()
            else:
                self.show_error(err)

        self.job_queue.submit("EngineFlow", _worker, on_success=_on_success, on_error=_on_error)

    def dock_screen(self):
        prof = self.profiles_data[self.profile_combo.currentText()]
        res = prof["res"]
        dpi = prof["dpi"]

        # Yatay/Dikey hesaplama
        w_res, h_res = map(int, res.split("x"))
        if self.landscape:
            target_res = f"{max(w_res, h_res)}x{min(w_res, h_res)}"
            aspect = max(w_res, h_res) / min(w_res, h_res)
            # Slot boyutunu ayarla
            h = 520
            w = int(h * aspect)
        else:
            target_res = f"{min(w_res, h_res)}x{max(w_res, h_res)}"
            aspect = max(w_res, h_res) / min(w_res, h_res)
            h = 760
            w = int(h / aspect)

        self.screen_slot.setFixedSize(w, h)

        # Cihaz ekran çözünürlüğünü ayarla
        self.adb.set_display(target_res, dpi)

        mode = self.settings.get("embed_mode")
        self.scrcpy.start(DEVICE_SERIAL, self.adb.adb_path, mode=mode)

    def on_scrcpy_embedded(self):
        self.placeholder_lbl.hide()
        self.set_status(T("✅ Ekran Başarıyla Kenetlendi", "✅ Screen Successfully Docked"))
        if self.settings.get("logcat_visible") and not self.logcat_widget.reader:
            self.logcat_widget.start_logging()

    def on_scrcpy_failed(self, msg: str):
        self.placeholder_lbl.show()
        self.set_status(T(f"⚠ Ekran Kenetlenemedi: {msg}", f"⚠ Docking Failed: {msg}"))

    def on_scrcpy_exited(self, code: int):
        self.placeholder_lbl.show()
        self.set_status(T(f"Ekran kapandı (kod {code})", f"Screen closed (code {code})"))

    # -------------------------------------------------------------
    # KULLANICI ETKİLEŞİMLERİ & PENCERELER
    # -------------------------------------------------------------
    def apply_device_profile(self):
        if self.adb.is_online():
            self.dock_screen()

    def toggle_rotation(self):
        self.landscape = not self.landscape
        self.settings.set("landscape", self.landscape)
        if self.adb.is_online():
            self.adb.set_rotation(1 if self.landscape else 0)
            self.dock_screen()

    def update_cam_toggle_button(self):
        if self.camera_live:
            self.btn_cam_toggle.setText(T("🟢 Kamera: AÇIK", "🟢 Camera: ON"))
            self.btn_cam_toggle.setStyleSheet("background-color: #1B5E20; font-weight: bold; border: 1px solid #4CAF50;")
        else:
            self.btn_cam_toggle.setText(T("🔴 Kamera: KAPALI", "🔴 Camera: OFF"))
            self.btn_cam_toggle.setStyleSheet("background-color: #B71C1C; font-weight: bold; border: 1px solid #FF5252;")

    def toggle_camera_privacy(self):
        self.camera_live = not self.camera_live
        self.settings.set("camera_enabled", self.camera_live)
        self.update_cam_toggle_button()
        if self.adb.is_online():
            self.adb.set_camera_privacy(not self.camera_live)
            if self.last_installed_pkg:
                self.adb.set_appop_camera(self.last_installed_pkg, self.camera_live)
            self.set_status(T("Kamera gizlilik durumu güncellendi.", "Camera privacy state updated."))

    def open_apk_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            T("Paket Seç (.apk, .xapk, .apks)", "Select Package (.apk, .xapk, .apks)"),
            "",
            "Android Packages (*.apk *.xapk *.apks *.apkm);;All Files (*.*)"
        )
        if path:
            self.process_incoming_file(path)

    def process_incoming_file(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in APK_EXTENSIONS:
            try:
                bundle = prepare_bundle(file_path, self.settings.get("ram_mb"), self.sdk.find_aapt())
                self.settings.add_recent_apk(file_path)
                self.start_engine_flow(apk_bundle=bundle)
            except ApkError as e:
                self.show_error(str(e))
        else:
            # Standart dosya ise cihazın /sdcard/Download/ klasörüne gönder
            if self.adb.is_online():
                self.set_status(T(f"Dosya gönderiliyor: {os.path.basename(file_path)}...", f"Pushing file: {os.path.basename(file_path)}..."))
                ok = self.adb.push(file_path)
                if ok:
                    self.set_status(T("✅ Dosya /sdcard/Download/ klasörüne gönderildi.", "✅ File pushed to /sdcard/Download/."))
                else:
                    self.show_error(T("Dosya cihaza aktarılamadı.", "Failed to push file."))
            else:
                self.show_error(T("Dosya aktarımı için emülatör açık olmalı.", "Emulator must be running for file push."))

    def relaunch_last_apk(self):
        if not self.adb.is_online():
            self.set_status(T("⚠ Emülatör açık değil!", "⚠ Emulator is not running!"))
            return
        if not self.last_installed_pkg:
            pkgs = self.adb.list_packages(third_party=True)
            if pkgs:
                self.last_installed_pkg = pkgs[-1]
        if self.last_installed_pkg:
            self.adb.launch(self.last_installed_pkg)
            self.set_status(T(f"Başlatıldı: {self.last_installed_pkg}", f"Launched: {self.last_installed_pkg}"))
        else:
            self.set_status(T("Henüz kurulu APK bulunamadı.", "No installed APK found yet."))

    def take_screenshot(self):
        if not self.adb.is_online():
            self.set_status(T("⚠ Emülatör açık değil!", "⚠ Emulator is not running!"))
            return
        out_dir = media_dir()
        filename = f"screenshot_{int(time.time())}.png"
        dest = os.path.join(out_dir, filename)
        if self.adb.screencap(dest):
            self.set_status(T(f"📸 Ekran görüntüsü kaydedildi: {filename}", f"📸 Screenshot saved: {filename}"))
        else:
            self.show_error(T("Ekran görüntüsü alınamadı.", "Failed to capture screenshot."))

    def toggle_logcat(self):
        vis = not self.logcat_widget.isVisible()
        self.logcat_widget.setVisible(vis)
        self.settings.set("logcat_visible", vis)
        if vis and self.adb.is_online():
            self.logcat_widget.start_logging()
        else:
            self.logcat_widget.stop_logging()

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec_() == SettingsDialog.Accepted:
            self.apply_theme()

    def open_apps_dialog(self):
        dlg = AppsDialog(self.adb, on_launch_callback=lambda pkg: self.set_status(f"Başlatıldı: {pkg}"), parent=self)
        dlg.exec_()

    def open_simulation_dialog(self):
        dlg = SimulationDialog(self.adb, self.settings, self)
        dlg.exec_()

    def open_setup_wizard(self):
        wiz = SetupWizardDialog(self.sdk, self.settings, self)
        wiz.installation_finished.connect(lambda avd: self.start_engine_flow())
        wiz.exec_()

    # -------------------------------------------------------------
    # SÜRÜKLE & BIRAK VE PENCERE OLAYLARI
    # -------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.process_incoming_file(path)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "scrcpy"):
            self.scrcpy.sync_geometry()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "scrcpy"):
            self.scrcpy.sync_geometry()

    def closeEvent(self, event):
        self.job_queue.cancel_all()
        if hasattr(self, "logcat_widget"):
            self.logcat_widget.stop_logging()
        if hasattr(self, "scrcpy"):
            self.scrcpy.stop()

        if self.settings.get("reset_display_on_exit") and self.adb.is_online():
            self.adb.reset_display()

        if self.settings.get("kill_emulator_on_exit"):
            self.emulator.stop(wait=5)

        event.accept()
