@echo off
title Building StreamVault Pro Executable
cd /d "%~dp0"
echo ========================================================
echo  Building StreamVault Pro Standalone (.exe)
echo ========================================================
echo.
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "StreamVaultPro" --collect-all yt_dlp --collect-all openpyxl --collect-all et_xmlfile --collect-all pywebview --collect-all clr_loader --collect-all pythonnet --add-data "core;core" web_app.py

if %ERRORLEVEL% EQU 0 (
    if exist "ffmpeg.exe" (
        echo Bundling portable ffmpeg.exe into dist directory...
        copy /y "ffmpeg.exe" "dist\StreamVaultPro\ffmpeg.exe" >nul
    )
    echo Stripping redundant .py source files to prevent Windows Defender locks...
    powershell -NoProfile -Command "Get-ChildItem -Path 'dist\StreamVaultPro' -Recurse -Filter '*.py' | Remove-Item -Force"
    echo.
    echo ========================================================
    echo  Build Successful!
    echo  Output folder: dist\StreamVaultPro\
    echo  Executable:    dist\StreamVaultPro\StreamVaultPro.exe
    echo ========================================================
    echo.
    set ISCC_PATH=""
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC_PATH="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC_PATH="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC_PATH="%ProgramFiles%\Inno Setup 6\ISCC.exe"

    if not %ISCC_PATH%=="" (
        echo Compiling Windows Installer (StreamVaultPro_Setup.exe)...
        %ISCC_PATH% installer.iss
        echo ========================================================
        echo  Installer created at: dist_installer\StreamVaultPro_Setup.exe
        echo ========================================================
    )
) else (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
)
