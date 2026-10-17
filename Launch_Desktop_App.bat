@echo off
title Video Downloader Desktop App
cd /d "%~dp0"
echo Launching Video Downloader Desktop Window...
.venv\Scripts\python.exe run_app.py
pause
