@echo off
title StreamVault Pro (Browser Mode)
cd /d "%~dp0"
echo Starting StreamVault Pro in Browser Mode...
.venv\Scripts\python.exe web_app.py --browser
pause
