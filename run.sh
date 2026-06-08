#!/bin/bash

# Dynamically set the working directory to the folder this script is in
cd "$(dirname "$0")"

clear
echo "======================================================="
echo "   Checking System Configurations and Dependencies..."
echo "======================================================="

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "[Error] Python 3 is not installed. Please install it to continue."
    exit 1
fi

# Silent dependency check
python3 -c "import flask, qrcode" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[System Status] Dependencies verified. Skipping module installation."
else
    echo "[System Status] Requirements missing. Installing only what is needed..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[Error] Failed to install required modules."
        exit 1
    fi
fi

echo "[System Status] Launching Server..."
while true; do
    python3 local_drop.py
    echo ""
    echo "[Warning] Connection dropped or network band shifted."
    echo "Re-initializing in 3 seconds to resume sharing... (Press Ctrl+C to quit)"
    sleep 3
done
