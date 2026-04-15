#!/bin/bash
# Netsurge Wireless NMS Desktop Launcher

echo "Starting Netsurge Wireless NMS..."

cd "$(dirname "$0")"

python3 -m src.desktop_launcher

echo "Press Enter to exit..."
read
