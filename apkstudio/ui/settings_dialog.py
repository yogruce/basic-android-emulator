"""Ayarlar ve Yapılandırma İletişim Kutusu."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QPushButton, QTabWidget, QWidget,
    QFormLayout, QMessageBox
)
from ..i18n import T
from ..constants import camera_modes, gpu_modes, network_speeds, network_delays, GPS_PRESETS
from ..settings import Settings

class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(T("Ayarlar", "Settings"))
        self.resize(500, 420)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # Sekme 1: Genel
        tab_general = QWidget()
        lay_gen = QFormLayout(tab_general)
        lay_gen.setSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Türkçe", "tr")
        self.lang_combo.addItem("English", "en")
        idx_lang = self.lang_combo.findData(self.settings.get("language"))
        if idx_lang >= 0:
            self.lang_combo.setCurrentIndex(idx_lang)
        lay_gen.addRow(T("Dil / Language:", "Language:"), self.lang_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(T("Karanlık (Dark)", "Dark"), "dark")
        self.theme_combo.addItem(T("Aydınlık (Light)", "Light"), "light")
        idx_theme = self.theme_combo.findData(self.settings.get("theme"))
        if idx_theme >= 0:
            self.theme_combo.setCurrentIndex(idx_theme)
        lay_gen.addRow(T("Tema:", "Theme:"), self.theme_combo)

        self.chk_updates = QCheckBox(T("Açılışta scrcpy güncellemelerini denetle", "Check for scrcpy updates on startup"))
        self.chk_updates.setChecked(self.settings.get("check_updates"))
        lay_gen.addRow("", self.chk_updates)

        self.chk_kill_exit = QCheckBox(T("Çıkışta emülatörü otomatik kapat", "Auto-kill emulator on exit"))
        self.chk_kill_exit.setChecked(self.settings.get("kill_emulator_on_exit"))
        lay_gen.addRow("", self.chk_kill_exit)

        self.chk_reset_disp = QCheckBox(T("Çıkışta ekran çözünürlüğünü sıfırla", "Reset display resolution on exit"))
        self.chk_reset_disp.setChecked(self.settings.get("reset_display_on_exit"))
        lay_gen.addRow("", self.chk_reset_disp)

        tabs.addTab(tab_general, T("Genel", "General"))

        # Sekme 2: Emülatör & Donanım
        tab_emu = QWidget()
        lay_emu = QFormLayout(tab_emu)
        lay_emu.setSpacing(10)

        self.gpu_combo = QComboBox()
        gpus = gpu_modes()
        for k, v in gpus.items():
            self.gpu_combo.addItem(v, k)
        idx_gpu = self.gpu_combo.findData(self.settings.get("gpu"))
        if idx_gpu >= 0:
            self.gpu_combo.setCurrentIndex(idx_gpu)
        lay_emu.addRow(T("GPU Modu:", "GPU Mode:"), self.gpu_combo)

        self.ram_spin = QSpinBox()
        self.ram_spin.setRange(2048, 16384)
        self.ram_spin.setSingleStep(1024)
        self.ram_spin.setSuffix(" MB")
        self.ram_spin.setValue(self.settings.get("ram_mb"))
        lay_emu.addRow(T("RAM Miktarı:", "RAM Size:"), self.ram_spin)

        self.cpu_spin = QSpinBox()
        self.cpu_spin.setRange(1, 16)
        self.cpu_spin.setValue(self.settings.get("cpu_cores"))
        lay_emu.addRow(T("CPU Çekirdek Sayısı:", "CPU Cores:"), self.cpu_spin)

        self.chk_quick_boot = QCheckBox(T("Hızlı Başlatma (Quick Boot / Snapshot) kullan", "Use Quick Boot / Snapshot"))
        self.chk_quick_boot.setChecked(self.settings.get("quick_boot"))
        lay_emu.addRow("", self.chk_quick_boot)

        self.boot_timeout_spin = QSpinBox()
        self.boot_timeout_spin.setRange(60, 900)
        self.boot_timeout_spin.setSingleStep(30)
        self.boot_timeout_spin.setSuffix(" sn")
        self.boot_timeout_spin.setValue(self.settings.get("boot_timeout"))
        lay_emu.addRow(T("Açılış Zaman Aşımı:", "Boot Timeout:"), self.boot_timeout_spin)

        tabs.addTab(tab_emu, T("Emülatör", "Emulator"))

        # Sekme 3: Gelişmiş & Pencere
        tab_adv = QWidget()
        lay_adv = QFormLayout(tab_adv)
        lay_adv.setSpacing(10)

        self.embed_combo = QComboBox()
        self.embed_combo.addItem(T("Alt Pencere (SetParent - Titremesiz)", "Child Window (SetParent)"), "child")
        self.embed_combo.addItem(T("Overlay Takip (Gerektiğinde)", "Overlay Tracking"), "overlay")
        idx_embed = self.embed_combo.findData(self.settings.get("embed_mode"))
        if idx_embed >= 0:
            self.embed_combo.setCurrentIndex(idx_embed)
        lay_adv.addRow(T("Ekran Kenetleme Modu:", "Screen Docking Mode:"), self.embed_combo)

        tabs.addTab(tab_adv, T("Gelişmiş", "Advanced"))

        layout.addWidget(tabs)

        # Alt Butonlar
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_save = QPushButton(T("Kaydet", "Save"))
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self.save)
        btn_box.addWidget(btn_save)

        btn_cancel = QPushButton(T("İptal", "Cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        layout.addLayout(btn_box)

    def save(self):
        old_lang = self.settings.get("language")
        new_lang = self.lang_combo.currentData()
        self.settings.set("language", new_lang)
        self.settings.set("theme", self.theme_combo.currentData())
        self.settings.set("check_updates", self.chk_updates.isChecked())
        self.settings.set("kill_emulator_on_exit", self.chk_kill_exit.isChecked())
        self.settings.set("reset_display_on_exit", self.chk_reset_disp.isChecked())

        self.settings.set("gpu", self.gpu_combo.currentData())
        self.settings.set("ram_mb", self.ram_spin.value())
        self.settings.set("cpu_cores", self.cpu_spin.value())
        self.settings.set("quick_boot", self.chk_quick_boot.isChecked())
        self.settings.set("boot_timeout", self.boot_timeout_spin.value())

        self.settings.set("embed_mode", self.embed_combo.currentData())
        self.settings.sync()

        if old_lang != new_lang:
            QMessageBox.information(
                self,
                T("Bilgi", "Notice"),
                T("Dil değişikliğinin tam uygulanması için uygulamayı yeniden başlatın.",
                  "Please restart the application for the language changes to take full effect.")
            )

        self.accept()
