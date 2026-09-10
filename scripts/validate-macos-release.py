#!/usr/bin/env python3
"""验证 macOS App 的结构、依赖、迁移、启动和视频编码。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _write_test_png(path: Path) -> None:
    width = height = 16
    rows = b"".join(b"\x00" + (b"\x30\x80\xf0" * width) for _ in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(rows))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def _run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, env=env)


def _validate_macho_dependencies(app: Path, executable: Path, ffmpeg: Path) -> int:
    candidates = {executable, ffmpeg, *app.rglob("*.dylib"), *app.rglob("*.so")}
    for framework in app.rglob("*.framework"):
        binary = framework / "Versions" / "A" / framework.stem
        if binary.is_file():
            candidates.add(binary)
    checked = 0
    for candidate in sorted(candidates):
        kind = _run(["file", str(candidate)])
        if "Mach-O" not in kind.stdout:
            continue
        if "arm64" not in kind.stdout:
            raise RuntimeError(f"发现不含 arm64 的 Mach-O：{candidate.name}")
        linked = _run(["otool", "-L", str(candidate)])
        if linked.returncode:
            raise RuntimeError(f"无法检查动态依赖：{candidate.name}")
        if "/opt/homebrew" in linked.stdout or "/usr/local" in linked.stdout:
            raise RuntimeError(f"发现本机开发环境依赖：{candidate.name}")
        checked += 1
    return checked


def validate(app: Path) -> dict[str, object]:
    info_path = app / "Contents" / "Info.plist"
    executable = app / "Contents" / "MacOS" / "旭影工具箱"
    if not info_path.is_file() or not executable.is_file():
        raise RuntimeError("App 结构不完整。")
    info = plistlib.loads(info_path.read_bytes())
    expected = {
        "CFBundleIdentifier": "com.xuying.toolbox.v2",
        "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "13.0",
    }
    for key, value in expected.items():
        if str(info.get(key)) != value:
            raise RuntimeError(f"Info.plist 的 {key} 不符合预期。")

    ffmpeg_candidates = tuple(app.rglob("ffmpeg"))
    ffmpeg = next((path for path in ffmpeg_candidates if path.is_file()), None)
    if ffmpeg is None:
        raise RuntimeError("发布包内缺少 FFmpeg。")
    macho_files_checked = _validate_macho_dependencies(app, executable, ffmpeg)
    ffmpeg_version = _run([str(ffmpeg), "-version"])
    if ffmpeg_version.returncode or "ffmpeg version 9.0.1" not in ffmpeg_version.stdout:
        raise RuntimeError("内置 FFmpeg 版本不符合预期。")
    forbidden_flags = ("--enable-gpl", "--enable-nonfree", "libx264")
    if any(flag in ffmpeg_version.stdout for flag in forbidden_flags):
        raise RuntimeError("内置 FFmpeg 含不允许的 GPL/nonfree 构建参数。")

    required_licenses = {
        "ExifRead-LICENSE.txt",
        "FFmpeg-LGPL-2.1.txt",
        "LGPL-3.0.txt",
        "NOTICE.md",
        "Python-3.12-LICENSE.txt",
        "Send2Trash-LICENSE.txt",
    }
    bundled_license_names = {path.name for path in app.rglob("licenses/*") if path.is_file()}
    missing_licenses = required_licenses - bundled_license_names
    if missing_licenses:
        raise RuntimeError(f"发布包缺少许可证：{sorted(missing_licenses)}")

    signature = _run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    if signature.returncode:
        raise RuntimeError(signature.stderr.strip() or "代码签名验证失败。")
    signature_details = _run(["codesign", "-dv", "--verbose=4", str(app)])
    ad_hoc_signature = "Signature=adhoc" in signature_details.stderr
    gatekeeper = _run(["spctl", "--assess", "--type", "execute", "--verbose=4", str(app)])

    with tempfile.TemporaryDirectory(prefix="xuying-stage7-") as temporary_name:
        temporary = Path(temporary_name)
        home = temporary / "home"
        legacy_root = home / "Library" / "Application Support" / "旭影工具箱"
        legacy_root.mkdir(parents=True)
        legacy_settings = legacy_root / "ui_config.json"
        legacy_settings.write_text('{"skin":"soft_3d"}', encoding="utf-8")
        legacy_hash = hashlib.sha256(legacy_settings.read_bytes()).hexdigest()
        cleanup_root = home / "Library" / "Application Support" / "摄影文件后期处理助手"
        cleanup_root.mkdir(parents=True)
        recovery = cleanup_root / "recovery-copy.jpg"
        recovery.write_bytes(b"safe recovery fixture")
        legacy_cleanup = cleanup_root / "cleanup_undo.json"
        legacy_cleanup.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "original_path": str(home / "Pictures" / "missing.jpg"),
                            "recovery_path": str(recovery),
                            "recovery_method": "copy",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        cleanup_hash = hashlib.sha256(legacy_cleanup.read_bytes()).hexdigest()
        env = os.environ.copy()
        env.update({"HOME": str(home), "PATH": "/usr/bin:/bin", "XUYING_AUTO_QUIT_MS": "1200"})
        launch = _run([str(executable)], env=env)
        if launch.returncode:
            raise RuntimeError(launch.stderr.strip() or "隔离用户首次启动失败。")
        migrated = legacy_root / "v2" / "application_settings.json"
        migrated_payload = json.loads(migrated.read_text(encoding="utf-8"))
        if migrated_payload.get("themeId") != "soft_3d":
            raise RuntimeError("隔离用户外观迁移失败。")
        if hashlib.sha256(legacy_settings.read_bytes()).hexdigest() != legacy_hash:
            raise RuntimeError("首次启动修改了旧版设置。")
        migrated_cleanup = legacy_root / "v2" / "cleanup_undo.json"
        if migrated_cleanup.read_bytes() != legacy_cleanup.read_bytes():
            raise RuntimeError("隔离用户清理恢复记录迁移失败。")
        if hashlib.sha256(legacy_cleanup.read_bytes()).hexdigest() != cleanup_hash:
            raise RuntimeError("首次启动修改了旧版清理恢复记录。")

        frames = temporary / "frames"
        frames.mkdir()
        _write_test_png(frames / "000001.png")
        _write_test_png(frames / "000002.png")
        video = temporary / "smoke.mp4"
        encode = _run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-framerate",
                "30/1",
                "-i",
                str(frames / "%06d.png"),
                "-c:v",
                "h264_videotoolbox",
                "-b:v",
                "8M",
                "-allow_sw",
                "1",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(video),
            ]
        )
        if encode.returncode or not video.is_file() or video.stat().st_size == 0:
            raise RuntimeError(encode.stderr.strip() or "内置 FFmpeg 视频导出失败。")

    return {
        "app": app.name,
        "bundleIdentifier": expected["CFBundleIdentifier"],
        "version": "2.0.0-rc.1",
        "architecture": "arm64",
        "minimumSystem": expected["LSMinimumSystemVersion"],
        "signatureVerified": True,
        "adHocSignature": ad_hoc_signature,
        "gatekeeperAccepted": gatekeeper.returncode == 0,
        "machOFilesChecked": macho_files_checked,
        "isolatedFirstLaunch": True,
        "legacySettingsUnchanged": True,
        "legacyCleanupMigrated": True,
        "legacyCleanupUnchanged": True,
        "bundledFfmpeg": True,
        "bundledFfmpegSystemDependenciesOnly": True,
        "bundledFfmpegMp4Export": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    arguments = parser.parse_args()
    report = validate(arguments.app.resolve())
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
