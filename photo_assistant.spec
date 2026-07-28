# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_dir = Path(SPEC).resolve().parent
app_name = "旭影的摄影工具集"

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
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
    target_arch="universal2",
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name=f"{app_name}.app",
    icon=str(project_dir / "assets" / "app_icon.icns"),
    bundle_identifier="com.nerophotographer.photo-post-assistant",
    info_plist={
        "CFBundleDisplayName": app_name,
        "CFBundleName": app_name,
        "CFBundleShortVersionString": "1.0.10",
        "CFBundleVersion": "11",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "恢复清理文件时，需要通过 Finder 将文件从废纸篓移回原文件夹。",
        "NSHumanReadableCopyright": "Copyright © 2026",
    },
)
