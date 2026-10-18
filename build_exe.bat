@echo off
title Building StreamVault Pro Executable
cd /d "%~dp0"
echo ========================================================
echo  Building StreamVault Pro Standalone (.exe)
echo ========================================================
echo.
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "StreamVaultPro" --icon "assets\icon.ico" --version-file "version_info.txt" --collect-all yt_dlp --collect-all openpyxl --collect-all et_xmlfile --collect-all pywebview --collect-all clr_loader --collect-all pythonnet --add-data "core;core" --add-data "assets;assets" web_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed. Please check the logs above.
    exit /b %ERRORLEVEL%
)

if exist "ffmpeg.exe" (
    echo Bundling portable ffmpeg.exe into dist directory...
    copy /y "ffmpeg.exe" "dist\StreamVaultPro\ffmpeg.exe" >nul
)

echo Stripping redundant .py source files to prevent Windows Defender locks...
powershell -NoProfile -Command "Get-ChildItem -Path 'dist\StreamVaultPro' -Recurse -Filter '*.py' | Remove-Item -Force"

echo Packaging clean portable zip (0 loose .py files)...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\StreamVaultPro' -DestinationPath 'StreamVaultPro.zip' -Force"

echo.
echo ========================================================
echo  Build Successful!
echo  Output folder: dist\StreamVaultPro\
echo  Executable:    dist\StreamVaultPro\StreamVaultPro.exe
echo  Portable Zip:  StreamVaultPro.zip
echo ========================================================
echo.

powershell -NoProfile -Command "$iscc = Get-ChildItem -Path '$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe', 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe', 'C:\Program Files\Inno Setup 6\ISCC.exe' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName; if ($iscc) { Write-Host 'Compiling Windows Installer (StreamVaultPro_Setup.exe)...'; & $iscc installer.iss; Write-Host '========================================================'; Write-Host ' Installer created at: dist_installer\StreamVaultPro_Setup.exe'; Write-Host '========================================================' }"
