"""本地文件系统两阶段重命名事务。"""

from __future__ import annotations

import uuid
from pathlib import Path

from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress


def run_two_phase_rename(
    pairs: list[tuple[Path, Path]],
    progress: ProgressCallback | None = None,
) -> None:
    """用随机临时名改名；失败时尽力恢复全部源路径。"""

    active = [(source, target) for source, target in pairs if source != target]
    source_keys = {str(source).casefold() for source, _ in active}
    target_keys: set[str] = set()
    for source, target in active:
        if not source.exists():
            raise FileNotFoundError(f"源文件不存在：{source}")
        target_key = str(target).casefold()
        if target_key in target_keys or (target.exists() and target_key not in source_keys):
            raise FileExistsError(f"目标路径冲突：{target}")
        target_keys.add(target_key)

    staged: list[tuple[Path, Path, Path]] = []
    completed: list[tuple[Path, Path]] = []
    total_steps = len(active) * 2
    report_progress(progress, 0, total_steps, f"正在准备文件 0/{len(active)}")
    try:
        for index, (source, target) in enumerate(active, start=1):
            temporary = source.with_name(f".{source.name}.xuying-{uuid.uuid4().hex}.tmp")
            source.rename(temporary)
            staged.append((source, temporary, target))
            report_progress(
                progress,
                index,
                total_steps,
                f"正在准备文件 {index}/{len(active)} · {source.name}",
            )
        for index, (source, temporary, target) in enumerate(staged, start=1):
            temporary.rename(target)
            completed.append((source, target))
            report_progress(
                progress,
                len(active) + index,
                total_steps,
                f"正在写入新名称 {index}/{len(active)} · {source.name} → {target.name}",
            )
    except Exception:
        for source, target in reversed(completed):
            if target.exists() and not source.exists():
                target.rename(source)
        for source, temporary, _ in reversed(staged):
            if temporary.exists() and not source.exists():
                temporary.rename(source)
        raise


class LocalRenameTransaction:
    def run(
        self,
        pairs: list[tuple[Path, Path]],
        progress: ProgressCallback | None = None,
    ) -> None:
        run_two_phase_rename(pairs, progress)
