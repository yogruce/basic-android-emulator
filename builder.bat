@echo off
chcp 65001 >nul
title APK Studio Player - Tek Tıkla Kurulum ve Derleyici
cd /d "%~dp0"

echo ========================================================
echo   APK STUDIO PLAYER - OTOMATİK KURULUM VE DERLEYİCİ
echo ========================================================
echo.

:: 1. Python Kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadı!
    echo Lütfen Python 3.10 veya daha güncel bir sürüm yükleyin ve "Add to PATH" kutucuğunu işaretleyin.
    echo İndirme: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/3] Gerekli Python kütüphaneleri kontrol ediliyor ve yükleniyor...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Bağımlılıklar yüklenirken bir sorun oluştu!
    pause
    exit /b 1
)
echo      -> Kütüphaneler hazır.
echo.

echo [2/3] Tek Dosya .EXE derleniyor (APK_Studio_Player.exe)...
echo      Lütfen bekleyin, bu işlem yaklaşık 30-60 saniye sürebilir...
python setup_and_build.py
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Derleme işlemi başarısız oldu!
    pause
    exit /b 1
)
echo.

echo [3/3] Derleme tamamlandı!
echo.
echo ========================================================
echo   KURULUM BAŞARIYLA TAMAMLANDI!
echo   Çalıştırılabilir Dosya: dist\APK_Studio_Player.exe
echo ========================================================
echo.

set /p START_NOW="Uygulamayı şimdi başlatmak ister misiniz? (E/H): "
if /i "%START_NOW%"=="E" (
    start "" "dist\APK_Studio_Player.exe"
)

echo.
echo Çıkmak için bir tuşa basın...
pause >nul
