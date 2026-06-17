#!/bin/bash

# Dynamically set working directory
cd "$(dirname "$0")"
clear

echo "======================================================="
echo "   Initializing Local Drop Environment..."
echo "======================================================="

# 1. Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[Error] Python 3 is not installed. Please install it to continue."
    exit 1
fi

# 2. Virtual Environment Generator
if [ ! -d "venv" ]; then
    echo "[Setup] Creating isolated Virtual Environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[Error] Failed to create venv. On some Linux distros, you may need to run: sudo apt install python3-venv"
        exit 1
    fi
fi

# 3. Activate the Virtual Environment
source venv/bin/activate

# 4. Silent Dependency Check (Inside venv)
python3 -c "import flask, qrcode" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[System] Dependencies verified."
else
    echo "[Setup] Installing required packages securely..."
    pip install -r requirements.txt
fi

# 5. Launch Application
echo "[System] Launching Server..."
while true; do
    python3 local_drop.py
    echo ""
    echo "[Warning] Connection dropped or network band shifted."
    echo "Re-initializing in 3 seconds to resume sharing... (Press Ctrl+C to quit)"
    sleep 3
done