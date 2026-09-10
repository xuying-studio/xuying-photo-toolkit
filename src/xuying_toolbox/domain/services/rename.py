"""时间重命名的纯 Python 规划与事务辅助逻辑。"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from pathlib import Path

from xuying_toolbox.domain.models.photo import (
    JPG_EXTENSIONS,
    RAW_EXTENSIONS,
    RenameOperation,
    RenamePlan,
    RenameScanStats,
)
from xuying_toolbox.domain.ports.metadata import MetadataReader
from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress

RENAMED_STEM_RE = re.compile(
    r"^DSC(?P<date>\d{2}-\d{2}-\d{2})-(?P<counter>\d{5})$",
    re.IGNORECASE,
)


def extract_original_number(filename: str) -> str | None:
    """提取文件名中的第一段连续数字。"""
    match = re.search(r"(\d+)", Path(filename).stem)
    return match.group(1) if match else None


def sidecar_target_for_rename(image_source: Path, image_target: Path, sidecar_source: Path) -> Path:
    standard = f"{image_source.stem}.xmp".casefold()
    if sidecar_source.name.casefold() == standard:
        return image_target.with_suffix(sidecar_source.suffix)
    return image_target.with_name(f"{image_target.name}{sidecar_source.suffix}")


def build_rename_plan(
    files: Iterable[Path],
    metadata_reader: MetadataReader,
    *,
    sidecars_by_image: Mapping[Path, Iterable[Path]] | None = None,
    path_exists: Callable[[Path], bool] | None = None,
    progress: ProgressCallback | None = None,
) -> RenamePlan:
    """按同目录编号分组，生成只读的照片和侧车改名计划。"""
    paths = sorted(files, key=lambda p: str(p).casefold())
    groups: dict[tuple[str, str], list[Path]] = {}
    capture_times: dict[tuple[str, str], datetime] = {}
    warnings: list[str] = []
    existing_counters: dict[str, int] = {}
    already_named = skipped = 0
    total_steps = len(paths) * 2 + 1
    report_progress(progress, 0, total_steps, f"正在读取照片信息 0/{len(paths)}")
    for index, path in enumerate(paths, start=1):
        match = RENAMED_STEM_RE.match(path.stem)
        if match:
            date_text = match.group("date")
            existing_counters[date_text] = max(
                existing_counters.get(date_text, 0),
                int(match.group("counter")),
            )
            already_named += 1
        else:
            number = extract_original_number(path.name)
            if number is None:
                skipped += 1
                warnings.append(f"未找到原始编号，已跳过：{path}")
            else:
                key = (str(path.parent).casefold(), number)
                groups.setdefault(key, []).append(path)
                stamp = metadata_reader.capture_time(path)
                if key not in capture_times or stamp < capture_times[key]:
                    capture_times[key] = stamp
        report_progress(
            progress,
            index,
            total_steps,
            f"正在读取拍摄时间 {index}/{len(paths)}",
        )

    ordered = sorted(
        ((capture_times[key], key, members) for key, members in groups.items()),
        key=lambda item: (item[0], item[1][1], str(item[2][0]).casefold()),
    )
    operations: list[RenameOperation] = []
    last_date: str | None = None
    counter = 0
    planned_files = 0
    sidecar_mapping = sidecars_by_image or {}
    report_progress(
        progress,
        len(paths),
        total_steps,
        f"正在生成重命名预览 0/{len(paths)}",
    )
    for stamp, _key, members in ordered:
        date_text = stamp.strftime("%y-%m-%d")
        if date_text != last_date:
            last_date = date_text
            counter = existing_counters.get(date_text, 0) + 1
        else:
            counter += 1
        for source in sorted(members, key=lambda p: p.suffix.casefold()):
            target = source.with_name(f"DSC{date_text}-{counter:05d}{source.suffix}")
            if source != target:
                operations.append(RenameOperation(str(source), str(target), "照片"))
            if source.suffix.casefold() in RAW_EXTENSIONS:
                sidecars = list(sidecar_mapping.get(source, ()))
                if len(sidecars) > 1:
                    warnings.append(f"发现多个 XMP 侧车，将全部保留命名方式处理：{source}")
                for sidecar in sidecars:
                    side_target = sidecar_target_for_rename(source, target, sidecar)
                    if sidecar != side_target:
                        operations.append(
                            RenameOperation(str(sidecar), str(side_target), "XMP 侧车")
                        )
            planned_files += 1
            report_progress(
                progress,
                len(paths) + planned_files,
                total_steps,
                f"正在生成重命名预览 {planned_files}/{len(paths)}",
            )
    conflicts = find_rename_conflicts(operations, path_exists=path_exists)
    stats = RenameScanStats(
        total_images=len(paths),
        raw_count=sum(p.suffix.casefold() in RAW_EXTENSIONS for p in paths),
        jpg_count=sum(p.suffix.casefold() in JPG_EXTENSIONS for p in paths),
        already_named_count=already_named,
        skipped_count=skipped,
        xmp_count=sum(op.kind == "XMP 侧车" for op in operations),
    )
    report_progress(progress, total_steps, total_steps, f"扫描完成 {len(paths)}/{len(paths)}")
    return RenamePlan(
        operations, sum(op.kind == "照片" for op in operations), conflicts, warnings, stats
    )


def find_rename_conflicts(
    operations: list[RenameOperation],
    *,
    path_exists: Callable[[Path], bool] | None = None,
) -> list[str]:
    exists = path_exists or (lambda _path: False)
    source_keys = {str(Path(operation.source)).casefold() for operation in operations}
    targets: dict[str, tuple[Path, int]] = {}
    for op in operations:
        target = Path(op.target)
        key = str(target).casefold()
        previous = targets.get(key)
        targets[key] = (target, 1 if previous is None else previous[1] + 1)
    conflicts: list[str] = []
    for key, (target, count) in targets.items():
        if count > 1:
            conflicts.append(f"多个文件将被重命名为同一路径：{target}")
        elif exists(target) and key not in source_keys:
            conflicts.append(f"目标文件已经存在：{target}")
    return conflicts
