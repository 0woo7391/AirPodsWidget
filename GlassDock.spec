# -*- mode: python ; coding: utf-8 -*-
# Glass dock prototype as a Windows app: prototypes/glass_dock/dock.py with its
# QML, icons and fonts at the bundle root (dock.py reads them from sys._MEIPASS).
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

hiddenimports = (collect_submodules("bleak") + collect_submodules("winrt")
                 + ["audio_backend", "media_backend", "device_backend", "demo_backends", "features"])

a = Analysis(
    ["prototypes/glass_dock/dock.py"],
    pathex=["prototypes/glass_dock", "prototypes/audio_widget_concepts", "prototypes/glass_audio_widget", "src"],
    binaries=[],
    datas=[
        ("prototypes/glass_dock/qml", "qml"),
        ("prototypes/audio_widget_concepts/assets/lucian-icons.json", "assets"),
        ("assets/fonts", "assets/fonts"),
        ("assets/app.ico", "assets"),
    ] + (
        # User-supplied and git-ignored (README); without it the dock simply stays silent.
        [("assets/low_power_warning.mp3", "assets")] if Path("assets/low_power_warning.mp3").exists() else []
    ),
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
    name="GlassDock",
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
    name="GlassDock",
)
