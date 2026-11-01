# 🚀 APK Studio Player

Modern, bağımsız ve hızlı Android APK test & emülatör oynatıcı.

## Özellikler

- **Yerel & Bağımsız:** Android SDK ve ARM destekli Android 12L sistem imajı tek tıkla otomatik kurulur.
- **Hafif ve Hızlı:** scrcpy v5 (SDL3) motoru kullanılarak sıfır gecikme ve kesintisiz görüntü aktarımı sağlanır.
- **Kesin Paket Algılama:** İkili AndroidManifest.xml (AXML) ayrıştırıcı ile APK, XAPK ve APKS paketleri doğrudan tanınır ve anında açılır.
- **Çoklu Cihaz Profilleri:** Samsung Galaxy S24 Ultra, Pixel 8 Pro, Tab S9, iPad Pro oranları ve 16:9 Kiosk modları.
- **Gelişmiş Geliştirici Araçları:**
  - Gerçek zamanlı Logcat görüntüleyici ve filtreleme
  - Cihaz simülasyonu (GPS, Ağ hızı, Pil ve şarj durumu)
  - Yüklü 3. taraf uygulamaları yönetme (başlat, durdur, veri temizle, kaldır)
  - Tek tıkla ekran görüntüsü alma
- **Gelişmiş Pencere Kenetleme:** Windows `SetParent` API ile titremesiz alt pencere entegrasyonu.

## Kurulum ve Çalıştırma

### ⚡ Tek Tıkla Kurulum ve EXE Derleme (Önerilen):
Projeyi indirdikten sonra doğrudan **`builder.bat`** dosyasına çift tıklayın:
1. Gerekli Python kütüphanelerini otomatik yükler.
2. `dist/APK_Studio_Player.exe` dosyasını tek tıkla derler.
3. İsteğe bağlı olarak uygulamayı anında başlatır.

### Kaynak Koddan Doğrudan Çalıştırma:
```bash
pip install -r requirements.txt
python main.py
```
veya **`baslat.bat`** dosyasını çalıştırabilirsiniz.

### Tek Dosya EXE Derleme (Komut Satırından):
```bash
python setup_and_build.py
```
