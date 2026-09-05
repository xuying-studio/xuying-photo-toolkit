# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path(SPEC).resolve().parent
app_name = "旭影工具箱"
vibrancy_library = project_dir / "build" / "native" / "libxuying_vibrancy.dylib"

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[(str(vibrancy_library), ".")],
    datas=[
        (str(project_dir / "assets" / "app_icon.png"), "assets"),
        (str(project_dir / "assets" / "app_icon_header.png"), "assets"),
    ],
    hiddenimports=["exifread", "send2trash"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name=f"{app_name}.app",
    icon=str(project_dir / "assets" / "app_icon.icns"),
    bundle_identifier="com.nerophotographer.photo-post-assistant.embedded",
    info_plist={
        "CFBundleDisplayName": app_name,
        "CFBundleName": app_name,
        "CFBundleShortVersionString": "1.4.0",
        "CFBundleVersion": "23",
        "LSMinimumSystemVersion": "13.0",
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "恢复清理文件时，需要通过 Finder 将文件从废纸篓移回原文件夹。",
        "NSHumanReadableCopyright": "Copyright © 2026",
    },
)
