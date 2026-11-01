"""GPS Konum, Ağ Hızı ve Pil Simülasyonu İletişim Kutusu."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QGroupBox,
    QFormLayout, QMessageBox
)
from ..i18n import T
from ..constants import GPS_PRESETS, network_speeds, network_delays
from ..settings import Settings

class SimulationDialog(QDialog):
    def __init__(self, adb_client, settings: Settings, parent=None):
        super().__init__(parent)
        self.adb = adb_client
        self.settings = settings
        self.setWindowTitle(T("Cihaz Simülasyonu", "Device Simulation"))
        self.resize(420, 480)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. GPS Simülasyonu
        grp_gps = QGroupBox(T("📍 Konum (GPS)", "📍 Location (GPS)"))
        lay_gps = QFormLayout(grp_gps)

        self.combo_presets = QComboBox()
        self.combo_presets.addItem(T("-- Şehir Seçin --", "-- Select City --"), None)
        for name, coords in GPS_PRESETS.items():
            self.combo_presets.addItem(name, coords)
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selected)
        lay_gps.addRow(T("Hazır Konum:", "Preset:"), self.combo_presets)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setValue(self.settings.get("gps_lat"))
        lay_gps.addRow(T("Enlem (Latitude):", "Latitude:"), self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setValue(self.settings.get("gps_lon"))
        lay_gps.addRow(T("Boylam (Longitude):", "Longitude:"), self.lon_spin)

        btn_apply_gps = QPushButton(T("Konumu Gönder", "Send Location"))
        btn_apply_gps.clicked.connect(self.apply_gps)
        lay_gps.addRow("", btn_apply_gps)

        layout.addWidget(grp_gps)

        # 2. Ağ Simülasyonu
        grp_net = QGroupBox(T("📶 Ağ Koşulları (Network)", "📶 Network Conditions"))
        lay_net = QFormLayout(grp_net)

        self.speed_combo = QComboBox()
        for k, v in network_speeds().items():
            self.speed_combo.addItem(v, k)
        lay_net.addRow(T("Hız Profili:", "Speed:"), self.speed_combo)

        self.delay_combo = QComboBox()
        for k, v in network_delays().items():
            self.delay_combo.addItem(v, k)
        lay_net.addRow(T("Gecikme (Latency):", "Delay:"), self.delay_combo)

        btn_apply_net = QPushButton(T("Ağ Ayarını Uygula", "Apply Network Settings"))
        btn_apply_net.clicked.connect(self.apply_network)
        lay_net.addRow("", btn_apply_net)

        layout.addWidget(grp_net)

        # 3. Pil Durumu
        grp_battery = QGroupBox(T("🔋 Pil & Şarj", "🔋 Battery & Power"))
        lay_bat = QFormLayout(grp_battery)

        self.battery_spin = QSpinBox()
        self.battery_spin.setRange(0, 100)
        self.battery_spin.setValue(100)
        self.battery_spin.setSuffix(" %")
        lay_bat.addRow(T("Pil Seviyesi:", "Battery Level:"), self.battery_spin)

        self.chk_charging = QCheckBox(T("Şarj Oluyor (AC Bağlı)", "Charging (AC Connected)"))
        self.chk_charging.setChecked(True)
        lay_bat.addRow("", self.chk_charging)

        btn_apply_bat = QPushButton(T("Pil Durumunu Uygula", "Apply Battery State"))
        btn_apply_bat.clicked.connect(self.apply_battery)
        lay_bat.addRow("", btn_apply_bat)

        layout.addWidget(grp_battery)

        # Kapat Butonu
        btn_close = QPushButton(T("Kapat", "Close"))
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def on_preset_selected(self):
        coords = self.combo_presets.currentData()
        if coords:
            lat, lon = coords
            self.lat_spin.setValue(lat)
            self.lon_spin.setValue(lon)

    def apply_gps(self):
        if not self.adb.is_online():
            QMessageBox.warning(self, T("Uyarı", "Warning"), T("Cihaz bağlı değil!", "Device not online!"))
            return
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        self.adb.geo_fix(lat, lon)
        self.settings.set("gps_lat", lat)
        self.settings.set("gps_lon", lon)
        QMessageBox.information(self, T("Bilgi", "Notice"), T(f"GPS ayarlandı: {lat:.4f}, {lon:.4f}", f"GPS set: {lat:.4f}, {lon:.4f}"))

    def apply_network(self):
        if not self.adb.is_online():
            QMessageBox.warning(self, T("Uyarı", "Warning"), T("Cihaz bağlı değil!", "Device not online!"))
            return
        speed = self.speed_combo.currentData()
        delay = self.delay_combo.currentData()
        self.adb.network(speed, delay)
        QMessageBox.information(self, T("Bilgi", "Notice"), T("Ağ profili uygulandı.", "Network profile applied."))

    def apply_battery(self):
        if not self.adb.is_online():
            QMessageBox.warning(self, T("Uyarı", "Warning"), T("Cihaz bağlı değil!", "Device not online!"))
            return
        level = self.battery_spin.value()
        charging = self.chk_charging.isChecked()
        self.adb.battery(level, charging)
        QMessageBox.information(self, T("Bilgi", "Notice"), T("Pil durumu uygulandı.", "Battery state applied."))
