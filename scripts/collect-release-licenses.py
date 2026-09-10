#!/usr/bin/env python3
"""收集发布包所需的许可证原文。"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path
from urllib.request import urlretrieve

REMOTE_LICENSES = {
    "LGPL-3.0.txt": (
        "https://www.gnu.org/licenses/lgpl-3.0.txt",
        "e3a994d82e644b03a792a930f574002658412f62407f5fee083f2555c5f23118",
    ),
    "GPL-3.0.txt": (
        "https://www.gnu.org/licenses/gpl-3.0.txt",
        "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_distribution_license(name: str, output: Path, output_name: str) -> None:
    package = distribution(name)
    candidates = [
        item
        for item in (package.files or ())
        if item.name.upper().startswith(("LICENSE", "COPYING"))
    ]
    if not candidates:
        raise RuntimeError(f"{name} 没有可收集的许可证文件。")
    source = Path(package.locate_file(candidates[0]))
    shutil.copyfile(source, output / output_name)


def collect(root: Path, output: Path) -> None:
    downloads = root / "build" / "downloads"
    ffmpeg_source = root / "build" / "ffmpeg-source" / "ffmpeg-9.0.1"
    output.mkdir(parents=True, exist_ok=True)

    for name, (url, expected_hash) in REMOTE_LICENSES.items():
        cached = downloads / name
        if not cached.is_file():
            downloads.mkdir(parents=True, exist_ok=True)
            urlretrieve(url, cached)
        if _sha256(cached) != expected_hash:
            raise RuntimeError(f"{name} 校验失败。")
        shutil.copyfile(cached, output / name)

    python_license = Path(sys.base_prefix) / "lib" / "python3.12" / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("找不到 Python 许可证文件。")
    shutil.copyfile(python_license, output / "Python-3.12-LICENSE.txt")
    _copy_distribution_license("ExifRead", output, "ExifRead-LICENSE.txt")
    _copy_distribution_license("Send2Trash", output, "Send2Trash-LICENSE.txt")
    _copy_distribution_license("PyInstaller", output, "PyInstaller-COPYING.txt")
    shutil.copyfile(ffmpeg_source / "COPYING.LGPLv2.1", output / "FFmpeg-LGPL-2.1.txt")
    shutil.copyfile(ffmpeg_source / "COPYING.GPLv2", output / "GPL-2.0.txt")
    shutil.copyfile(root / "docs" / "legal" / "THIRD_PARTY_NOTICES.md", output / "NOTICE.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    collect(arguments.root.resolve(), arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
