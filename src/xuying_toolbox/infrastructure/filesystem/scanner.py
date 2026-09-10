"""本地文件扫描与 XMP 侧车发现。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from xuying_toolbox.domain.models.photo import IMAGE_EXTENSIONS


def iter_files(folder: str | Path, recursive: bool) -> Iterable[Path]:
    root = Path(folder)
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        # 不跟随符号链接，避免批量操作越出用户确认的文件夹。
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            relative_parts = path.parts
        if any(part.startswith(".") for part in relative_parts):
            continue
        yield path


def iter_image_files(folder: str | Path, recursive: bool = False) -> list[Path]:
    """返回稳定排序的受支持照片；产品默认不递归。"""

    return sorted(
        (
            path
            for path in iter_files(folder, recursive)
            if path.suffix.casefold() in IMAGE_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )


def find_sidecars(image_path: Path) -> list[Path]:
    wanted = {
        f"{image_path.stem}.xmp".casefold(),
        f"{image_path.name}.xmp".casefold(),
    }
    try:
        return sorted(
            (
                path
                for path in image_path.parent.iterdir()
                if path.is_file() and path.name.casefold() in wanted
            ),
            key=lambda path: (
                path.name.casefold() != f"{image_path.stem}.xmp".casefold(),
                path.name.casefold(),
            ),
        )
    except OSError:
        return []


def sidecar_target_for_rename(
    image_source: Path,
    image_target: Path,
    sidecar_source: Path,
) -> Path:
    standard_name = f"{image_source.stem}.xmp".casefold()
    if sidecar_source.name.casefold() == standard_name:
        return image_target.with_suffix(sidecar_source.suffix)
    return image_target.with_name(f"{image_target.name}{sidecar_source.suffix}")


def preferred_sidecar(image_path: str | Path) -> Path:
    image = Path(image_path)
    sidecars = find_sidecars(image)
    if not sidecars:
        return image.with_suffix(".xmp")
    standard_name = f"{image.stem}.xmp".casefold()

    def priority(sidecar: Path) -> tuple[int, int]:
        try:
            modified = sidecar.stat().st_mtime_ns
        except OSError:
            modified = -1
        return modified, int(sidecar.name.casefold() == standard_name)

    return max(sidecars, key=priority)
