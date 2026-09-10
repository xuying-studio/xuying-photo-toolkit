"""关键词快切输入队列的纯路径规则。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".heic"})
_NATURAL_PART = re.compile(r"(\d+)")


def canonical_path(path: Path) -> Path:
    """解析绝对规范路径；不要求路径实际存在。"""
    return path.expanduser().resolve(strict=False)


def is_supported_image(path: Path) -> bool:
    return path.suffix.casefold() in SUPPORTED_IMAGE_EXTENSIONS


def natural_sort_key(path: Path) -> tuple[object, ...]:
    """按类似 Finder 的数字自然顺序排序，并以规范路径作稳定兜底。"""
    parts: list[object] = []
    for part in _NATURAL_PART.split(path.name.casefold()):
        parts.append(int(part) if part.isdigit() else part)
    return (*parts, str(canonical_path(path)).casefold())


def unique_supported_paths(
    candidates: Iterable[Path],
    existing: Iterable[Path] = (),
) -> tuple[list[Path], int, int]:
    """过滤候选并去重，返回新增路径、重复数和忽略数。"""
    seen = {str(canonical_path(path)).casefold() for path in existing}
    new_paths: list[Path] = []
    duplicates = ignored = 0
    for path in candidates:
        canonical = canonical_path(path)
        if (
            path.name.startswith(".")
            or path.is_symlink()
            or not path.is_file()
            or not is_supported_image(path)
        ):
            ignored += 1
            continue
        key = str(canonical).casefold()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        new_paths.append(canonical)
    return sorted(new_paths, key=natural_sort_key), duplicates, ignored
