"""İlk Kurulum Sihirbazı İletişim Kutusu (SDK / AVD Kurulumu ve Lisans Onayı)."""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QComboBox, QCheckBox, QTextBrowser, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from ..i18n import T
from ..sdk import Sdk, SdkInstaller, IMAGE_VARIANTS, LICENSE_URL
from ..settings import Settings
from ..jobs import JobQueue

class SetupWizardDialog(QDialog):
    installation_finished = pyqtSignal(str)  # avd_name

    def __init__(self, sdk: Sdk, settings: Settings, parent=None):
        super().__init__(parent)
        self.sdk = sdk
        self.settings = settings
        self.job_queue = JobQueue(self)
        self.installer = None
        self.created_avd = ""

        self.setWindowTitle(T("Android Motoru Kurulum Sihirbazı", "Android Engine Setup Wizard"))
        self.resize(520, 400)
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(T("🚀 Android Motoru ve Sanal Cihaz Kurulumu", "🚀 Android Engine & AVD Setup"))
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        desc = QLabel(T(
            "APK Studio'nun APK'ları bağımsız olarak çalıştırabilmesi için yerel Android motoru (SDK, Emulator ve ARM Native Bridge imajı) kurulacaktır.\n"
            "Bu işlem tek seferliktir ve yaklaşık 1.5 - 2.5 GB indirme gerektirir.",
            "A local Android engine (SDK, Emulator, and ARM Native Bridge system image) will be installed.\n"
            "This is a one-time setup and requires approximately 1.5 - 2.5 GB download."
        ))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # İmaj Seçimi
        h_img = QHBoxLayout()
        h_img.addWidget(QLabel(T("Sistem İmajı Türü:", "System Image Type:")))
        self.combo_img = QComboBox()
        for k, v in IMAGE_VARIANTS.items():
            self.combo_img.addItem(v, k)
        h_img.addWidget(self.combo_img)
        layout.addLayout(h_img)

        # Lisans Onayı
        lic_box = QVBoxLayout()
        self.chk_license = QCheckBox(T("Google Android SDK Lisans Sözleşmesini okudum ve kabul ediyorum.",
                                       "I have read and agree to the Google Android SDK License Terms."))
        self.chk_license.setChecked(self.settings.get("license_accepted"))
        self.chk_license.stateChanged.connect(self.on_license_toggle)

        btn_view_license = QPushButton(T("Lisans Metnini Aç (Web)", "View License (Web)"))
        btn_view_license.setFixedWidth(160)
        btn_view_license.clicked.connect(lambda: os.system(f"start {LICENSE_URL}"))

        lic_row = QHBoxLayout()
        lic_row.addWidget(self.chk_license)
        lic_row.addWidget(btn_view_license)
        layout.addLayout(lic_row)

        # Durum ve İlerleme
        self.lbl_status = QLabel(T("Kurulum için hazır.", "Ready to install."))
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton(T("Kurulumu Başlat", "Start Setup"))
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setEnabled(self.chk_license.isChecked())
        self.btn_start.clicked.connect(self.start_install)
        btn_row.addWidget(self.btn_start)

        self.btn_cancel = QPushButton(T("İptal", "Cancel"))
        self.btn_cancel.clicked.connect(self.cancel_or_close)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

        # JobQueue bağlantıları
        self.job_queue.status.connect(self.lbl_status.setText)
        self.job_queue.progress.connect(self.on_progress)
        self.job_queue.busy_changed.connect(self.on_busy_changed)

    def on_license_toggle(self, state):
        accepted = (state == Qt.Checked)
        self.btn_start.setEnabled(accepted and not self.job_queue.busy)
        self.settings.set("license_accepted", accepted)

    def on_progress(self, done, total):
        if total > 0:
            val = int(done * 100 / total)
            self.progress_bar.setValue(min(val, 100))
        else:
            self.progress_bar.setValue(0)

    def on_busy_changed(self, busy):
        self.btn_start.setEnabled(not busy and self.chk_license.isChecked())
        self.combo_img.setEnabled(not busy)
        self.btn_cancel.setText(T("İptal Et", "Cancel") if busy else T("Kapat", "Close"))

    def start_install(self):
        variant = self.combo_img.currentData()
        ram = self.settings.get("ram_mb")
        cores = self.settings.get("cpu_cores")

        def _do_install(job, v, r, c):
            installer = SdkInstaller(
                self.sdk,
                status=job.emit_status,
                progress=job.emit_progress,
                cancel=job.cancel_event
            )
            return installer.install(variant=v, ram_mb=r, cores=c)

        def _on_success(avd_name):
            self.created_avd = avd_name
            self.progress_bar.setValue(100)
            self.lbl_status.setText(T(f"✅ Kurulum Tamamlandı: {avd_name}", f"✅ Setup Complete: {avd_name}"))
            QMessageBox.information(
                self,
                T("Başarılı", "Success"),
                T(f"Android motoru ve '{avd_name}' sanal cihazı başarıyla kuruldu!",
                  f"Android engine and virtual device '{avd_name}' have been installed successfully!")
            )
            self.installation_finished.emit(avd_name)
            self.accept()

        def _on_error(err):
            self.lbl_status.setText(T(f"❌ Kurulum Hatası: {err}", f"❌ Setup Error: {err}"))
            QMessageBox.critical(self, T("Hata", "Error"), str(err))

        self.job_queue.submit(
            "SdkInstall",
            _do_install, variant, ram, cores,
            on_success=_on_success,
            on_error=_on_error
        )

    def cancel_or_close(self):
        if self.job_queue.busy:
            if QMessageBox.question(
                self,
                T("İptal", "Cancel"),
                T("Kurulum iptal edilsin mi? Yarım kalan indirmeler daha sonra devam edebilir.",
                  "Cancel installation? Incomplete downloads can resume later.")
            ) == QMessageBox.Yes:
                self.job_queue.cancel_all()
        else:
            self.reject()

    def closeEvent(self, event):
        if self.job_queue.busy:
            self.cancel_or_close()
            event.ignore()
        else:
            event.accept()
