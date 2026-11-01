# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None
base_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(base_dir, 'bin'), 'bin'),
]

a = Analysis(
    ['main.py'],
    pathex=[base_dir],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'apkstudio',
        'apkstudio.ui',
        'apkstudio.ui.main_window',
        'apkstudio.ui.settings_dialog',
        'apkstudio.ui.apps_dialog',
        'apkstudio.ui.simulation_dialog',
        'apkstudio.ui.setup_wizard',
        'apkstudio.ui.logcat_view',
        'apkstudio.ui.theme',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
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
    name='APK_Studio_Player',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(base_dir, 'bin', 'icon.png') if os.path.exists(os.path.join(base_dir, 'bin', 'icon.png')) else None,
)
