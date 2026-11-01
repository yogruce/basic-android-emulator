import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess

# Kurulumun yapılacağı standart yerel dizin (%LOCALAPPDATA%\Android\Sdk)
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
SDK_ROOT = os.path.join(LOCAL_APPDATA, "Android", "Sdk")
JDK_DIR = os.path.join(LOCAL_APPDATA, "Android", "PortableJDK")
AVD_HOME = os.path.join(os.path.expanduser("~"), ".android", "avd")

# Resmi İndirme Bağlantıları (Taşınabilir JDK 17 ve Google Command-Line Tools)
JDK_URL = "https://aka.ms/download-jdk/microsoft-jdk-17.0.10-windows-x64.zip"
CMDLINE_TOOLS_URL = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"

# İçinde yerleşik ARM -> x86_64 çeviricisi (Native Bridge) bulunan stabil Android 12L imajı
SYSTEM_IMAGE = "system-images;android-32;google_apis;x86_64"
AVD_NAME = "APK_Studio_ARM_Engine"


def download_with_progress(url, dest_path, title):
    print(f"\n📥 İndiriliyor: {title}")
    def progress(count, block_size, total_size):
        if total_size > 0:
            percent = min(int(count * block_size * 100 / total_size), 100)
            mb_done = (count * block_size) / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\r   İlerleme: %{percent} ({mb_done:.1f} MB / {mb_total:.1f} MB)")
            sys.stdout.flush()
    urllib.request.urlretrieve(url, dest_path, reporthook=progress)
    print("\n   -> İndirme tamamlandı!")


def setup_portable_jdk():
    """sdkmanager'ın çalışması için gereken Java 17 ortamını kurar (Sistemi kirletmez)."""
    os.makedirs(JDK_DIR, exist_ok=True)
    for item in os.listdir(JDK_DIR):
        java_exe = os.path.join(JDK_DIR, item, "bin", "java.exe")
        if os.path.exists(java_exe):
            print("✔ Taşınabilir JDK 17 zaten hazır.")
            return os.path.join(JDK_DIR, item)

    zip_path = os.path.join(JDK_DIR, "jdk17.zip")
    download_with_progress(JDK_URL, zip_path, "Taşınabilir OpenJDK 17 (Microsoft Build)")
    print("📦 JDK arşivden çıkarılıyor...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(JDK_DIR)
    os.remove(zip_path)

    for item in os.listdir(JDK_DIR):
        if os.path.exists(os.path.join(JDK_DIR, item, "bin", "java.exe")):
            return os.path.join(JDK_DIR, item)
    raise RuntimeError("JDK kurulumu doğrulanamadı!")


def setup_cmdline_tools():
    """Google Android SDK Command-Line Tools paketini doğru klasör hiyerarşisiyle kurar."""
    latest_dir = os.path.join(SDK_ROOT, "cmdline-tools", "latest")
    sdkmanager_bat = os.path.join(latest_dir, "bin", "sdkmanager.bat")

    if os.path.exists(sdkmanager_bat):
        print("✔ Android SDK Command-Line Tools zaten hazır.")
        return latest_dir

    os.makedirs( os.path.join(SDK_ROOT, "cmdline-tools"), exist_ok=True)
    zip_path = os.path.join(SDK_ROOT, "cmdline_tools.zip")
    download_with_progress(CMDLINE_TOOLS_URL, zip_path, "Google Android SDK Command-Line Tools")

    temp_extract = os.path.join(SDK_ROOT, "cmdline-tools", "temp")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_extract)
    os.remove(zip_path)

    extracted_inner = os.path.join(temp_extract, "cmdline-tools")
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)
    shutil.move(extracted_inner, latest_dir)
    shutil.rmtree(temp_extract, ignore_errors=True)
    return latest_dir


def run_sdk_command(cmd_list, env, auto_accept=True):
    """Lisansları ve soruları otomatik onaylayarak SDK komutlarını çalıştırır."""
    proc = subprocess.Popen(
        cmd_list,
        stdin=subprocess.PIPE,
        env=env,
        shell=True
    )
    if auto_accept:
        # Tüm lisans ve onay sorularına otomatik 'y' veya 'no' yanıtı gönderir
        input_data = ("y\n" * 40).encode("utf-8")
        proc.communicate(input=input_data)
    else:
        proc.communicate()
    return proc.returncode


def patch_avd_config(avd_name):
    """Oluşturulan sanal cihazın config.ini dosyasını yüksek performans için optimize eder."""
    config_path = os.path.join(AVD_HOME, f"{avd_name}.avd", "config.ini")
    if not os.path.exists(config_path):
        print(f"⚠ Uyarı: {config_path} bulunamadı, varsayılan ayarlar kullanılacak.")
        return

    with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    overrides = {
        "hw.ramSize": "4096",
        "hw.cpu.ncore": "4",
        "hw.gpu.enabled": "yes",
        "hw.gpu.mode": "host",       # Doğrudan ekran kartını (RTX) kullanır
        "hw.keyboard": "yes",        # Fiziksel klavye ile yazmayı aktif eder
        "hw.mainKeys": "no",         # Ekran içi sanal tuşları korur
        "disk.dataPartition.size": "8G"
    }

    existing_keys = set()
    new_lines = []
    for line in lines:
        if "=" in line:
            key = line.split("=")[0].strip()
            if key in overrides:
                new_lines.append(f"{key}={overrides[key]}\n")
                existing_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for key, val in overrides.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={val}\n")

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("⚡ AVD Donanım İvmesi (GPU=Host, 4GB RAM, 4 Çekirdek) başarıyla yamalandı!")


def main():
    print("=" * 65)
    print("🚀 APK STUDIO - OTONOM ANDROID MOTORU VE ARM İMAJ KURUCUSU")
    print("=" * 65)

    # 1. Taşınabilir Java 17 Kurulumu
    java_home = setup_portable_jdk()
    
    # 2. Android Command-Line Tools Kurulumu
    cmdline_dir = setup_cmdline_tools()

    # Ortam değişkenlerini hazırla
    env = os.environ.copy()
    env["JAVA_HOME"] = java_home
    env["ANDROID_SDK_ROOT"] = SDK_ROOT
    env["ANDROID_HOME"] = SDK_ROOT
    env["PATH"] = f"{os.path.join(java_home, 'bin')};{os.path.join(cmdline_dir, 'bin')};{env.get('PATH', '')}"

    sdkmanager_bat = os.path.join(cmdline_dir, "bin", "sdkmanager.bat")
    avdmanager_bat = os.path.join(cmdline_dir, "bin", "avdmanager.bat")

    # 3. Lisansları Onayla
    print("\n📜 [1/3] Google SDK Lisansları Otomatik Onaylanıyor...")
    run_sdk_command([sdkmanager_bat, f"--sdk_root={SDK_ROOT}", "--licenses"], env)

    # 4. Emulator, Platform-Tools ve ARM Çeviricili Sistem İmajını İndir
    print("\n🌐 [2/3] Android Motoru ve ARM Destekli Sistem İmajı İndiriliyor...")
    print("   (Not: Sistem imajı ~1.4 GB boyutundadır, internet hızınıza göre birkaç dakika sürebilir.)")
    packages = [
        "platform-tools",
        "emulator",
        "platforms;android-32",
        SYSTEM_IMAGE
    ]
    ret = run_sdk_command([sdkmanager_bat, f"--sdk_root={SDK_ROOT}"] + packages, env)
    if ret != 0:
        print("\n❌ Paketler indirilirken bir hata oluştu. İnternet bağlantınızı kontrol edin.")
        sys.exit(1)

    # 5. Sanal Cihazı (AVD) Oluştur
    print(f"\n📱 [3/3] '{AVD_NAME}' Sanal Cihazı Oluşturuluyor...")
    avd_cmd = [
        avdmanager_bat, "create", "avd",
        "-n", AVD_NAME,
        "-k", SYSTEM_IMAGE,
        "-d", "pixel_5",
        "--force"
    ]
    # avdmanager 'Do you wish to create a custom hardware profile [no]' sorusuna 'no' bekler
    proc = subprocess.Popen(avd_cmd, stdin=subprocess.PIPE, env=env, shell=True)
    proc.communicate(input=b"no\n")

    # 6. Performans ve GPU Yamasını Uygula
    patch_avd_config(AVD_NAME)

    print("\n" + "=" * 65)
    print("✅ KURULUM KUSURSUZ ŞEKİLDE TAMAMLANDI!")
    print(f"   Kurulan Motor Yolu : {SDK_ROOT}\\emulator\\emulator.exe")
    print(f"   Hazır Sanal Cihaz  : {AVD_NAME} (Android 12L + ARM Native Bridge)")
    print("\nArtık 'APK_Studio_Player.exe' uygulamanızı açıp doğrudan APK sürükleyebilirsiniz!")
    print("=" * 65)


if __name__ == "__main__":
    main()