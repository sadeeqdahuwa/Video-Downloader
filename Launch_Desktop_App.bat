@echo off
title StreamVault Pro Desktop App
cd /d "%~dp0"
echo Launching StreamVault Pro Desktop Window...
.venv\Scripts\python.exe run_app.py
pause
