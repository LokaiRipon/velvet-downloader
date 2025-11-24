# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs
)

block_cipher = None

# 🔑 Critical: Explicitly include yt-dlp.__main__ and all submodules
hiddenimports = [
    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # yt-dlp core — MUST include __main__ for bundled execution
    'yt_dlp',
    'yt_dlp.__main__',  # 👈 This ensures __main__.py is included
    'yt_dlp.extractor',
    'yt_dlp.extractor.youtube',
    'yt_dlp.postprocessor',
    'yt_dlp.utils',
    # Windows permissions
    'win32api',
    'win32security',
    'ntsecuritycon',
    'win32con',
] + collect_submodules('yt_dlp')  # Ensures all extractors (TikTok, Instagram, etc.) are bundled

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 🔥 collect_data_files(..., include_py_files=True) is ESSENTIAL to get __main__.py
    datas=collect_data_files('yt_dlp', include_py_files=True) + [
        ('audio.ico', '.'),
        ('vid.ico', '.'),
        ('icon.ico', '.'),  # ensure your app icon is included
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add pywin32 binaries
a.binaries += collect_dynamic_libs('pywin32')

# Optional: Manually include pywin32 DLLs (for Python 3.11 — adjust if needed)
if sys.platform == "win32":
    import site, os
    for sp in site.getsitepackages():
        dll_dir = os.path.join(sp, 'pywin32_system32')
        if os.path.isdir(dll_dir):
            for dll_name in ['pythoncom311.dll', 'pywintypes311.dll']:  # ← 311 = Python 3.11
                dll_path = os.path.join(dll_dir, dll_name)
                if os.path.isfile(dll_path):
                    if not any(dll_name == b[0] for b in a.binaries):
                        a.binaries.append((dll_name, dll_path, 'BINARY'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VelvetDown',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 👈 Final app should hide console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)