"""APK Studio Player - Tek Dosya Derleyici Script."""

import os
import sys
import subprocess

def build():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(base_dir, "APK_Studio_Player.spec")

    print("=" * 60)
    print("APK Studio Player PyInstaller ile Derleniyor...")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]

    subprocess.check_call(cmd, cwd=base_dir)

    exe_path = os.path.join(base_dir, "dist", "APK_Studio_Player.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"[OK] Derleme Basarili!\nEXE Yolu: {exe_path} ({size_mb:.1f} MB)")
        print("=" * 60)
    else:
        print("\n[HATA] EXE olusturulamadi!")

if __name__ == "__main__":
    build()
