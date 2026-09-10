"""时间重命名用例：只编排预览、事务和撤回。"""

from __future__ import annotations

from pathlib import Path

from xuying_toolbox.domain.models.photo import RAW_EXTENSIONS, RenamePlan
from xuying_toolbox.domain.ports.metadata import MetadataReader
from xuying_toolbox.domain.ports.photo_tools import (
    PhotoCatalog,
    RenameJournal,
    RenameTransaction,
)
from xuying_toolbox.domain.services.progress import ProgressCallback
from xuying_toolbox.domain.services.rename import (
    build_rename_plan,
    sidecar_target_for_rename,
)


class RenameUseCase:
    def __init__(
        self,
        catalog: PhotoCatalog,
        metadata_reader: MetadataReader,
        transaction: RenameTransaction,
        journal: RenameJournal,
    ) -> None:
        self.catalog = catalog
        self.metadata_reader = metadata_reader
        self.transaction = transaction
        self.journal = journal

    def scan(
        self,
        folder: str | Path,
        *,
        recursive: bool = False,
        progress: ProgressCallback | None = None,
    ) -> RenamePlan:
        files = self.catalog.images(folder, recursive)
        sidecars = {
            path: self.catalog.sidecars(path)
            for path in files
            if path.suffix.casefold() in RAW_EXTENSIONS
        }
        return build_rename_plan(
            files,
            self.metadata_reader,
            sidecars_by_image=sidecars,
            path_exists=self.catalog.exists,
            progress=progress,
        )

    def execute(
        self,
        plan: RenamePlan,
        progress: ProgressCallback | None = None,
    ) -> Path:
        if plan.conflicts:
            raise ValueError("计划存在冲突，不能执行。")
        if not plan.operations:
            raise ValueError("没有需要执行的重命名操作。")
        manifest = self.journal.create(plan)
        try:
            self.transaction.run(
                [(Path(operation.source), Path(operation.target)) for operation in plan.operations],
                progress,
            )
        except Exception as exc:
            try:
                self.journal.mark_failed(manifest, str(exc))
            except (OSError, ValueError):
                pass
            raise
        self.journal.mark_completed(manifest)
        return manifest

    def undo(self, progress: ProgressCallback | None = None) -> int:
        manifest = self.journal.latest()
        if manifest is None:
            raise FileNotFoundError("没有可撤回的重命名记录。")
        data = self.journal.load(manifest)
        operations = data.get("operations", [])
        pairs = [(Path(item["target"]), Path(item["source"])) for item in operations]
        original_targets = {target for _, target in pairs}
        current_sources = {source for source, _ in pairs}
        for item in operations:
            original_raw = Path(item["source"])
            renamed_raw = Path(item["target"])
            if item.get("kind") != "照片" or original_raw.suffix.casefold() not in RAW_EXTENSIONS:
                continue
            for sidecar in self.catalog.sidecars(renamed_raw):
                if sidecar in current_sources:
                    continue
                target = sidecar_target_for_rename(renamed_raw, original_raw, sidecar)
                if target in original_targets or self.catalog.exists(target):
                    raise FileExistsError(f"撤回目标已有同名文件：{target}")
                pairs.append((sidecar, target))
                current_sources.add(sidecar)
                original_targets.add(target)
        self.transaction.run(pairs, progress)
        self.journal.delete(manifest)
        return len(pairs)

    def has_undo(self) -> bool:
        """只读查询当前是否有已完成的撤回记录。"""

        return self.journal.latest() is not None


__all__ = ["RenameUseCase"]
