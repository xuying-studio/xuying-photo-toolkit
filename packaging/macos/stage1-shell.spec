# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).resolve().parents[1]
NATIVE_VISION = ROOT / "build" / "native" / "libXuyingVision.dylib"
NATIVE_VISUALS = ROOT / "build" / "native" / "libXuyingMacVisuals.dylib"
APP_ICON = ROOT / "build" / "macos" / "app_icon.icns"

a = Analysis(
    [str(ROOT / "scripts" / "package_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[
        (str(NATIVE_VISION), "native"),
        (str(NATIVE_VISUALS), "native"),
    ],
    datas=[(str(ROOT / "qml"), "qml")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="旭影工具箱",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="旭影工具箱",
)
app = BUNDLE(
    coll,
    name="旭影工具箱.app",
    icon=str(APP_ICON),
    bundle_identifier="com.xuying.toolbox.v2",
)
