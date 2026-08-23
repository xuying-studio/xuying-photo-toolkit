# -*- mode: python ; coding: utf-8 -*-
"""Windows x64 的 PyInstaller onedir 配置。"""

from pathlib import Path


project_dir = Path(SPEC).resolve().parent
app_name = "旭影的摄影工具集"
icon_path = project_dir / "assets" / "app_icon.ico"
version_info_path = project_dir / "windows_version_info.txt"
manifest_path = project_dir / "windows_app.manifest"

a = Analysis(
    [str(project_dir / "main.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        (str(project_dir / "assets" / "app_icon.png"), "assets"),
        (str(project_dir / "assets" / "app_icon_header.png"), "assets"),
    ],
    hiddenimports=[
        "exifread",
        "send2trash",
        "pythoncom",
        "pywintypes",
        "win32com.client",
    ],
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
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_path),
    version=str(version_info_path),
    manifest=str(manifest_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=app_name,
)
