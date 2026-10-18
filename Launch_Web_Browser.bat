@echo off
title StreamVault Pro
cd /d "%~dp0"
echo Starting StreamVault Pro Dashboard...
start http://127.0.0.1:5000
.venv\Scripts\python.exe web_app.py
pause
