@echo off
title Local Drop Launcher
cls

echo =======================================================
echo    Checking System Configurations and Dependencies...
echo =======================================================

:: Check if required Python modules are present without re-installing
python -c "import flask, qrcode" 2>NUL
if %errorlevel% equ 0 (
    echo [System Status] Dependencies verified. Skipping module installation.
    goto LAUNCH_PROCESS
)

echo [System Status] Requirements missing. Executing targeted package installation...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Dependency engine configuration failed. Confirm pip installation.
    pause
    exit /b
)

:LAUNCH_PROCESS
echo [System Status] Launching Application Module Loop...
:LOOP
:: The runtime execution handles network band disconnect tolerances gracefully 
python local_drop.py
echo [Warning] Server connection loop interrupted or dropped.
echo Re-initializing in 3 seconds... Press Ctrl+C to abort cleanly.
timeout /t 3 >nul
goto LOOP
