"""Yüklü üçüncü taraf uygulamaları listeleme ve yönetme penceresi."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox
)
from ..i18n import T

class AppsDialog(QDialog):
    def __init__(self, adb_client, on_launch_callback=None, parent=None):
        super().__init__(parent)
        self.adb = adb_client
        self.on_launch_callback = on_launch_callback
        self.setWindowTitle(T("Yüklü Uygulamalar", "Installed Applications"))
        self.resize(450, 400)
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel(T("Cihazda Yüklü 3. Taraf Uygulamalar:", "Installed 3rd Party Apps on Device:")))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_launch = QPushButton(T("▶ Başlat", "▶ Launch"))
        btn_launch.setObjectName("primaryBtn")
        btn_launch.clicked.connect(self.launch_selected)
        btn_row.addWidget(btn_launch)

        btn_stop = QPushButton(T("⏹ Durdur", "⏹ Stop"))
        btn_stop.clicked.connect(self.stop_selected)
        btn_row.addWidget(btn_stop)

        btn_clear = QPushButton(T("🧹 Veriyi Temizle", "🧹 Clear Data"))
        btn_clear.clicked.connect(self.clear_selected)
        btn_row.addWidget(btn_clear)

        btn_uninstall = QPushButton(T("🗑 Kaldır", "🗑 Uninstall"))
        btn_uninstall.setObjectName("dangerBtn")
        btn_uninstall.clicked.connect(self.uninstall_selected)
        btn_row.addWidget(btn_uninstall)

        layout.addLayout(btn_row)

        bottom_row = QHBoxLayout()
        btn_refresh = QPushButton(T("🔄 Yenile", "🔄 Refresh"))
        btn_refresh.clicked.connect(self.refresh_list)
        bottom_row.addWidget(btn_refresh)
        bottom_row.addStretch()

        btn_close = QPushButton(T("Kapat", "Close"))
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def get_selected(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def refresh_list(self):
        self.list_widget.clear()
        if not self.adb.is_online():
            self.list_widget.addItem(T("Cihaz çevrimdışı!", "Device is offline!"))
            return
        pkgs = self.adb.list_packages(third_party=True)
        if not pkgs:
            self.list_widget.addItem(T("Yüklü uygulama bulunamadı.", "No apps installed."))
            return
        for p in pkgs:
            self.list_widget.addItem(p)

    def launch_selected(self):
        pkg = self.get_selected()
        if not pkg or pkg.startswith("("):
            return
        ok = self.adb.launch(pkg)
        if ok and self.on_launch_callback:
            self.on_launch_callback(pkg)
        self.accept()

    def stop_selected(self):
        pkg = self.get_selected()
        if not pkg:
            return
        self.adb.force_stop(pkg)
        QMessageBox.information(self, T("Bilgi", "Notice"), T(f"{pkg} durduruldu.", f"{pkg} stopped."))

    def clear_selected(self):
        pkg = self.get_selected()
        if not pkg:
            return
        if QMessageBox.question(
            self,
            T("Onay", "Confirm"),
            T(f"{pkg} uygulamasının tüm verileri temizlensin mi?", f"Clear all data for {pkg}?")
        ) == QMessageBox.Yes:
            self.adb.clear_data(pkg)
            QMessageBox.information(self, T("Bilgi", "Notice"), T("Veri temizlendi.", "Data cleared."))

    def uninstall_selected(self):
        pkg = self.get_selected()
        if not pkg:
            return
        if QMessageBox.question(
            self,
            T("Onay", "Confirm"),
            T(f"{pkg} uygulaması tamamen kaldırılsın mı?", f"Completely uninstall {pkg}?")
        ) == QMessageBox.Yes:
            ok = self.adb.uninstall(pkg)
            if ok:
                QMessageBox.information(self, T("Bilgi", "Notice"), T("Uygulama kaldırıldı.", "App uninstalled."))
                self.refresh_list()
            else:
                QMessageBox.warning(self, T("Hata", "Error"), T("Kaldırılamadı.", "Uninstall failed."))
