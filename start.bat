@echo off
chcp 65001 >nul 2>&1
title Tencent Cloud Snap Up
cd /d "%~dp0"

echo ==================================================
echo   Tencent Cloud - Snap Up Script Launcher
echo ==================================================
echo:

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [CHECK] Checking dependencies...
python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo [INSTALL] Installing requests...
    python -m pip install requests
)

python -c "import playwright" 2>nul
if %errorlevel% neq 0 (
    echo [INSTALL] Installing playwright...
    python -m pip install playwright
    python -m playwright install chromium
)

echo:
echo [START] Launching snap_up.py ...
echo:
python snap_up.py

echo:
pause
