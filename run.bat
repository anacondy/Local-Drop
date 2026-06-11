@echo off
chcp 65001 >nul
title Local Drop

echo.
echo  =====================================================
echo        LOCAL DROP - STARTING UP
echo  =====================================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Please install Python 3.8+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo  [SETUP] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [SETUP] Virtual environment created.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install / upgrade dependencies silently
echo  [SETUP] Checking dependencies...
pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo  [SETUP] Dependencies OK.
echo.

:: Run the server
python local_drop.py

:: If server exits, pause so user can read any error
echo.
echo  Server stopped. Press any key to close.
pause >nul