@echo off
REM Netsurge Wireless NMS Desktop Launcher
REM Double-click to run the desktop launcher application

echo Starting Netsurge Wireless NMS...
cd /d "%~dp0"
python -m src.desktop_launcher
pause
