@echo off
title Local Drop Launcher
cls

:: This forces the terminal into the exact folder this file is located in
cd /d "%~dp0"

echo =======================================================
echo    Checking System Configurations and Dependencies...
echo =======================================================

:: Check if Python is installed at all
python --version >NUL 2>NUL
if %errorlevel% neq 0 (
    echo [Error] Python is not installed or not in PATH. Please install Python 3.
    pause
    exit /b
)

:: Silent dependency check
python -c "import flask, qrcode" 2>NUL
if %errorlevel% equ 0 (
    echo [System Status] Dependencies verified. Skipping module installation.
    goto LAUNCH_PROCESS
)

echo [System Status] Requirements missing. Installing only what is needed...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Dependency installation failed. Please check your internet connection.
    pause
    exit /b
)

:LAUNCH_PROCESS
echo [System Status] Launching Server...
:LOOP
python local_drop.py
echo.
echo [Warning] Connection dropped or network band shifted. 
echo Re-initializing in 3 seconds to resume sharing... (Press Ctrl+C to quit)
timeout /t 3 >nul
goto LOOP
