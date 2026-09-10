#!/usr/bin/env python3
"""生成发布目录的文件清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release_dir", type=Path)
    arguments = parser.parse_args()
    release_dir = arguments.release_dir.resolve()
    files = []
    for path in sorted(release_dir.rglob("*")):
        if not path.is_file() or path.name in {"release-manifest.json", "SHA256SUMS"}:
            continue
        files.append(
            {
                "name": str(path.relative_to(release_dir)),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    payload = {
        "product": "旭影工具箱",
        "version": "2.0.0-rc.1",
        "platform": "macOS",
        "architecture": "arm64",
        "minimumSystem": "13.0",
        "releaseStatus": "内部候选包；未完成 Developer ID 公证",
        "files": files,
    }
    output = release_dir / "release-manifest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksum_lines = []
    for path in sorted(release_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            checksum_lines.append(f"{_sha256(path)}  {path.relative_to(release_dir)}")
    (release_dir / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
