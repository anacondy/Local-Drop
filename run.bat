@echo off
title Local Drop Launcher
cls

:: Force terminal into the script's directory
cd /d "%~dp0"

echo =======================================================
echo    Initializing Local Drop Environment...
echo =======================================================

:: 1. Smart Python Targeter (Prefers 'py -3', falls back to 'python')
set PYTHON_CMD=python
py -3 --version >NUL 2>NUL
if %errorlevel% equ 0 set PYTHON_CMD=py -3

%PYTHON_CMD% --version >NUL 2>NUL
if %errorlevel% neq 0 (
    echo [Error] Python 3 is not installed or not in PATH.
    pause
    exit /b
)

:: 2. Virtual Environment Generator
if not exist "venv\Scripts\activate.bat" (
    echo [Setup] Creating isolated Virtual Environment...
    %PYTHON_CMD% -m venv venv
)

:: 3. Activate the Virtual Environment
call venv\Scripts\activate.bat

:: 4. Silent Dependency Check (Inside venv)
python -c "import flask, qrcode" 2>NUL
if %errorlevel% neq 0 (
    echo [Setup] Installing required packages securely...
    pip install -r requirements.txt
) else (
    echo [System] Dependencies verified.
)

:: 5. Launch Application
echo [System] Launching Server...
:LOOP
python local_drop.py
echo.
echo [Warning] Connection dropped or network band shifted. 
echo Re-initializing in 3 seconds to resume sharing... (Press Ctrl+C to quit)
timeout /t 3 >nul
goto LOOP
