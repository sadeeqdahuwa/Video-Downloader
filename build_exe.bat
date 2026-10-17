@echo off
title Building All Video Downloader Pro Executable
cd /d "%~dp0"
echo ========================================================
echo  Building All Video Downloader Pro Standalone (.exe)
echo ========================================================
echo.
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "AllVideoDownloaderPro" --collect-all yt_dlp --collect-all openpyxl --collect-all et_xmlfile --add-data "core;core" web_app.py

if %ERRORLEVEL% EQU 0 (
    if exist "ffmpeg.exe" (
        echo Bundling portable ffmpeg.exe into dist directory...
        copy /y "ffmpeg.exe" "dist\AllVideoDownloaderPro\ffmpeg.exe" >nul
    )
    echo.
    echo ========================================================
    echo  Build Successful!
    echo  Output folder: dist\AllVideoDownloaderPro\
    echo  Executable:    dist\AllVideoDownloaderPro\AllVideoDownloaderPro.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
)

