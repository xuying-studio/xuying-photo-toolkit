# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).resolve().parents[1]
NATIVE_VISION = ROOT / "build" / "native" / "libXuyingVision.dylib"
NATIVE_VISUALS = ROOT / "build" / "native" / "libXuyingMacVisuals.dylib"
FFMPEG = ROOT / "build" / "ffmpeg" / "bin" / "ffmpeg"
LICENSES = ROOT / "build" / "release-licenses"
APP_ICON = ROOT / "build" / "macos" / "app_icon.icns"

a = Analysis(
    [str(ROOT / "scripts" / "package_entry.py")],
    pathex=[str(ROOT / "src")],
    binaries=[
        (str(NATIVE_VISION), "native"),
        (str(NATIVE_VISUALS), "native"),
        (str(FFMPEG), "bin"),
    ],
    datas=[
        (str(ROOT / "qml"), "qml"),
        (str(LICENSES), "licenses"),
    ],
    hiddenimports=[],
    hookspath=[str(ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtPdf",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
    ],
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
    info_plist={
        "CFBundleDisplayName": "旭影工具箱",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "用于在用户确认后通过访达恢复最近一次清理。",
    },
)
