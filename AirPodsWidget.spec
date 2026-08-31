# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

hiddenimports = collect_submodules("bleak") + collect_submodules("winrt")

a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("assets/low_power_warning.mp3", "assets"),
        ("assets/app.ico", "assets"),
        ("assets/fonts", "assets/fonts"),
        ("src/ui", "src/ui"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

# Qt6Core resolves ICU symbols from the Windows ICU shim. PyInstaller can
# accidentally collect an incompatible icu*.dll from another PATH entry
# (for example Poppler), which then shadows the Windows copy at runtime.
a.binaries = [
    entry
    for entry in a.binaries
    if not Path(entry[0]).name.lower().startswith("icu")
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AirPodsWidget",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/app.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AirPodsWidget",
)
