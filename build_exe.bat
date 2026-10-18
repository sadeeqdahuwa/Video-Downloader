@echo off
title Building StreamVault Pro Executable
cd /d "%~dp0"
echo ========================================================
echo  Building StreamVault Pro Standalone (.exe)
echo ========================================================
echo.
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "StreamVaultPro" --collect-all yt_dlp --collect-all openpyxl --collect-all et_xmlfile --add-data "core;core" web_app.py

if %ERRORLEVEL% EQU 0 (
    if exist "ffmpeg.exe" (
        echo Bundling portable ffmpeg.exe into dist directory...
        copy /y "ffmpeg.exe" "dist\StreamVaultPro\ffmpeg.exe" >nul
    )
    echo.
    echo ========================================================
    echo  Build Successful!
    echo  Output folder: dist\StreamVaultPro\
    echo  Executable:    dist\StreamVaultPro\StreamVaultPro.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
)
