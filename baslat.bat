@echo off
chcp 65001 >nul
title APK Studio Player
cd /d "%~dp0"

echo ========================================================
echo   APK STUDIO PLAYER BAŞLATILIYOR...
echo ========================================================
echo.

if exist "dist\APK_Studio_Player.exe" (
    start "" "dist\APK_Studio_Player.exe"
) else (
    python main.py
)

if %errorlevel% neq 0 (
    echo.
    echo [HATA] Uygulama baslatilamadi!
    pause
)
