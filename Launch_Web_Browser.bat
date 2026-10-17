@echo off
title Video Downloader Web UI
cd /d "%~dp0"
echo Starting Video Downloader Web Dashboard...
start http://127.0.0.1:5000
.venv\Scripts\python.exe web_app.py
pause
