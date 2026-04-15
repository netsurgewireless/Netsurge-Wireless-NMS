# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import sys
from os.path import dirname, join

pystray_path = join(dirname(pystray.__file__), 'pystray')
pilstring_path = join(dirname(__file__), 'PIL')

a = Analysis(
    ['src/client.py'],
    pathex=[],
    binaries=[],
    datas=[
        (pystray_path + '/_pystray.pyd', '_pystray'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pystray._win32',
        'pystray._darwin',
        'pystray._linux',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='NetworkMonitorClient',
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
    icon='assets/icon.ico' if sys.platform == 'win32' else 'assets/icon.icns',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='NetworkMonitorClient.app',
        icon='assets/icon.icns',
        bundle_identifier='com.networkmonitor.client',
        info_plist={
            'CFBundleName': 'Network Monitor Client',
            'CFBundleDisplayName': 'Network Monitor Client',
            'LSMinimumSystemVersion': '10.13',
            'NSPrincipalClass': 'NSApplication',
            'LSUIElement': True,
        },
    )
