# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.__main__ import run

block_cipher = None

project_root = os.path.dirname(os.path.abspath(SPEC))

server_scripts = [
    ('src/server.py', 'src'),
    ('src/__init__.py', 'src'),
    ('src/models.py', 'src'),
    ('src/config.py', 'src'),
    ('src/storage.py', 'src'),
    ('src/alerts.py', 'src'),
    ('src/alert_handlers.py', 'src'),
    ('src/server_api.py', 'src'),
    ('src/dashboard.py', 'src'),
    ('src/ai_assistant.py', 'src'),
    ('src/ai_database.py', 'src'),
    ('src/ai_unified.py', 'src'),
    ('src/ai_sync.py', 'src'),
    ('src/device_cli.py', 'src'),
    ('src/device_routes.py', 'src'),
    ('src/server_optimize.py', 'src'),
    ('src/scheduler.py', 'src'),
]

monitors_scripts = [
    ('src/monitors/__init__.py', 'src/monitors'),
    ('src/monitors/ping.py', 'src/monitors'),
    ('src/monitors/port.py', 'src/monitors'),
    ('src/monitors/snmp.py', 'src/monitors'),
    ('src/monitors/http.py', 'src/monitors'),
    ('src/monitors/bandwidth.py', 'src/monitors'),
    ('src/monitors/discovery.py', 'src/monitors'),
    ('src/monitors/nginx.py', 'src/monitors'),
    ('src/monitors/server_health.py', 'src/monitors'),
    ('src/monitors/wireless.py', 'src/monitors'),
    ('src/monitors/wmi.py', 'src/monitors'),
    ('src/monitors/mibs.py', 'src/monitors'),
    ('src/monitors/ipmi.py', 'src/monitors'),
]

desktop_scripts = [
    ('src/desktop_launcher.py', 'src'),
    ('src/desktop_client.py', 'src'),
    ('src/client.py', 'src'),
    ('src/__main__.py', 'src'),
]

resources = []

for root, dirs, files in os.walk(project_root):
    if '__pycache__' in root or 'ai_cache' in root:
        continue
    for file in files:
        if file.endswith(('.json', '.txt', '.md')):
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, project_root)
            resources.append((full_path, rel_path))

a = Analysis(
    ['src/desktop_launcher.py'],
    pathex=[project_root],
    binaries=[],
    datas=resources,
    hiddenimports=[
        'flask',
        'pysnmp',
        'cryptography',
        'requests',
        'apscheduler',
        'paramiko',
        'tkinter',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test',
        'tests',
        'docs',
        '__pycache__',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Netsurge-NMS-Launcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpname=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Netsurge-Wireless-NMS',
)

print("Building installer for Windows...")
