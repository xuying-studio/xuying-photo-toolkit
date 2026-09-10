"""RAW/JPG 同目录配对与孤立文件清理的纯业务规则。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from xuying_toolbox.domain.models.photo import (
    JPG_EXTENSIONS,
    RAW_EXTENSIONS,
    CleanupItem,
    CleanupScanResult,
)
from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress


def scan_cleanup(
    files: Iterable[Path],
    delete_kind: str,
    progress: ProgressCallback | None = None,
) -> CleanupScanResult:
    """根据已扫描文件计算同目录、同主文件名的配对结果。"""

    kind = delete_kind.upper()
    if kind not in {"JPG", "RAW"}:
        raise ValueError("清理类型必须是 JPG 或 RAW。")

    files = sorted(files, key=lambda path: str(path).casefold())
    total_steps = len(files) * 2
    report_progress(progress, 0, total_steps, f"正在建立照片索引 0/{len(files)}")
    by_folder: dict[Path, dict[str, set[str]]] = {}
    for index, path in enumerate(files, start=1):
        by_folder.setdefault(path.parent, {}).setdefault(path.stem.casefold(), set()).add(
            path.suffix.casefold()
        )
        report_progress(
            progress,
            index,
            total_steps,
            f"正在建立照片索引 {index}/{len(files)}",
        )

    target_exts = JPG_EXTENSIONS if kind == "JPG" else RAW_EXTENSIONS
    pair_exts = RAW_EXTENSIONS if kind == "JPG" else JPG_EXTENSIONS
    missing_kind = "RAW" if kind == "JPG" else "JPG"
    items: list[CleanupItem] = []
    for index, path in enumerate(files, start=1):
        if path.suffix.casefold() in target_exts and by_folder[path.parent][
            path.stem.casefold()
        ].isdisjoint(pair_exts):
            items.append(CleanupItem(str(path), missing_kind))
        report_progress(
            progress,
            len(files) + index,
            total_steps,
            f"正在检查照片配对 {index}/{len(files)}",
        )
    items.sort(key=lambda item: item.path.casefold())
    target_count = sum(path.suffix.casefold() in target_exts for path in files)
    return CleanupScanResult(
        items=items,
        total_images=len(files),
        raw_count=sum(path.suffix.casefold() in RAW_EXTENSIONS for path in files),
        jpg_count=sum(path.suffix.casefold() in JPG_EXTENSIONS for path in files),
        target_count=target_count,
        paired_target_count=target_count - len(items),
    )


def build_cleanup_plan(files: Iterable[Path], delete_kind: str) -> list[CleanupItem]:
    """返回预览清单；兼容旧版只返回项目列表的调用方式。"""

    return scan_cleanup(files, delete_kind).items
