#!/bin/bash

# Configuration setup utility script for Linux and macOS environments
clear
echo "======================================================="
echo "   Checking System Configurations and Dependencies..."
echo "======================================================="

# Inline conditional verification module check
python3 -c "import flask, qrcode" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[System Status] Dependencies verified. Skipping module installation."
else
    echo "[System Status] Requirements missing. Executing targeted package installation..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[Error] Failed to install required modules via pip3."
        exit 1
    fi
fi

echo "[System Status] Launching Application Module Loop..."
while true; do
    # Loop keeps runtime system alive if network interfaces hop channels or bands
    python3 local_drop.py
    echo "[Warning] Server connection loop interrupted or dropped."
    echo "Re-initializing connection loop in 3 seconds..."
    sleep 3
done
