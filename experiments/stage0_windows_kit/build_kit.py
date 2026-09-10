"""把测试脚本、用户授权截图和 Mac 基线组装成 Windows ZIP。"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}


def copy_sources(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".venv", "work", "__pycache__", "*.pyc"),
    )
    results = destination / "results"
    results.mkdir(exist_ok=True)
    for path in results.iterdir():
        if path.name != ".gitkeep":
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def copy_images(source: Path, destination: Path) -> list[dict[str, object]]:
    destination.mkdir(parents=True, exist_ok=True)
    gitkeep = destination / ".gitkeep"
    if gitkeep.exists():
        gitkeep.unlink()
    manifest: list[dict[str, object]] = []
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix.casefold() not in ALLOWED_EXTENSIONS:
            continue
        target = destination / path.name
        shutil.copy2(path, target)
        with Image.open(target) as image:
            width, height = image.size
        manifest.append(
            {
                "file": path.name,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
                "bytes": target.stat().st_size,
            }
        )
    if not manifest:
        raise RuntimeError("截图目录中没有支持的图片。")
    return manifest


def write_zip(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source.parent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--vision-baseline", type=Path, required=True)
    parser.add_argument("--rapidocr-baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="xuying-stage0-windows-kit-") as temporary:
        package = Path(temporary) / "旭影阶段0-Windows测试包"
        copy_sources(source, package)
        files = copy_images(args.screenshots, package / "input" / "real")
        baselines = package / "mac-baseline"
        baselines.mkdir()
        shutil.copy2(args.vision_baseline, baselines / "ocr-apple-vision.json")
        shutil.copy2(args.rapidocr_baseline, baselines / "ocr-rapidocr-macos.json")
        (package / "input-manifest.json").write_text(
            json.dumps(
                {
                    "scope": "user-authorized-real-screenshots",
                    "keyword": (package / "keyword.txt").read_text(encoding="utf-8").strip(),
                    "source_count": len(files),
                    "total_bytes": sum(int(item["bytes"]) for item in files),
                    "files": files,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        write_zip(package, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
