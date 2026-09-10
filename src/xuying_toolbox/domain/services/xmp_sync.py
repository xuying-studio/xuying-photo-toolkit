"""XMP 双向同步的纯规划规则。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from xuying_toolbox.domain.models.photo import (
    JPG_EXTENSIONS,
    RAW_EXTENSIONS,
    SyncOperation,
    SyncScanResult,
)
from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress
from xuying_toolbox.domain.services.xmp import XmpProperties


def plan_sync(
    files: Iterable[Path],
    direction: str,
    sync_rating: bool,
    sync_label: bool,
    read_properties: Callable[[Path], XmpProperties],
    progress: ProgressCallback | None = None,
) -> SyncScanResult:
    if not sync_rating and not sync_label:
        raise ValueError("至少选择一种同步内容。")
    if direction not in {"JPG → RAW", "RAW → JPG"}:
        raise ValueError("同步方向无效。")

    paths = sorted(files, key=lambda path: str(path).casefold())
    source_exts = JPG_EXTENSIONS if direction == "JPG → RAW" else RAW_EXTENSIONS
    target_exts = RAW_EXTENSIONS if direction == "JPG → RAW" else JPG_EXTENSIONS
    sources = [path for path in paths if path.suffix.casefold() in source_exts]
    candidates: dict[tuple[str, str], list[Path]] = {}
    for path in paths:
        if path.suffix.casefold() in target_exts:
            key = (str(path.parent).casefold(), path.stem.casefold())
            candidates.setdefault(key, []).append(path)
    pair_index = {
        key: sorted(values, key=lambda path: path.suffix.casefold())[0]
        for key, values in candidates.items()
    }

    operations: list[SyncOperation] = []
    matched = 0
    marked = 0
    up_to_date = 0
    report_progress(progress, 0, len(sources), f"正在读取 XMP 标记 0/{len(sources)}")
    for index, source in enumerate(sources, start=1):
        target = pair_index.get((str(source.parent).casefold(), source.stem.casefold()))
        if target is not None:
            matched += 1
            source_properties = read_properties(source)
            target_properties = read_properties(target)
            rating = (
                source_properties.rating if sync_rating and source_properties.rating > 0 else None
            )
            label = source_properties.label if sync_label and source_properties.label else None
            if rating is not None or label is not None:
                marked += 1
                if (rating is None or rating == target_properties.rating) and (
                    label is None or label == target_properties.label
                ):
                    up_to_date += 1
                else:
                    operations.append(
                        SyncOperation(
                            source=str(source),
                            target=str(target),
                            target_is_raw=direction == "JPG → RAW",
                            rating=rating,
                            label=label,
                            old_rating=target_properties.rating,
                            old_label=target_properties.label,
                        )
                    )
        report_progress(
            progress,
            index,
            len(sources),
            f"正在读取 XMP 标记 {index}/{len(sources)}",
        )

    return SyncScanResult(
        operations=operations,
        total_images=len(paths),
        source_count=len(sources),
        target_count=sum(path.suffix.casefold() in target_exts for path in paths),
        matched_count=matched,
        marked_count=marked,
        up_to_date_count=up_to_date,
    )
