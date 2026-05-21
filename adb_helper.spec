# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

hiddenimports = (
    collect_submodules("PySide6.QtWebEngineWidgets")
    + collect_submodules("PySide6.QtWebEngineCore")
    + [
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
        "PySide6.QtWebChannel",
        "PySide6.QtNetwork",
        "darkdetect",
    ]
)

datas = [
    ("assets/fonts/", "assets/fonts/"),
    ("db/migrations/", "db/migrations/"),
    ("frontend_dist", "frontend_dist"),
]
# PySide6 ships the WebEngine .pak / locale assets next to the package — the
# default hook copies them, but be explicit so the build fails fast if the
# expected layout ever changes.
datas += collect_data_files("PySide6", subdir="Qt/resources")
datas += collect_data_files("PySide6", subdir="Qt/translations/qtwebengine_locales")

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
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

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="adb_helper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="adb_helper",
)
