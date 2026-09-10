"""Adobe XMP 双向同步用例，只编排规划和事务端口。"""

from __future__ import annotations

from pathlib import Path

from xuying_toolbox.domain.models.photo import SyncOperation, SyncScanResult
from xuying_toolbox.domain.ports.photo_tools import (
    PhotoCatalog,
    XmpRepository,
    XmpTransaction,
)
from xuying_toolbox.domain.services.progress import ProgressCallback
from xuying_toolbox.domain.services.xmp_sync import plan_sync


class XmpSyncUseCase:
    def __init__(
        self,
        catalog: PhotoCatalog,
        repository: XmpRepository,
        transaction: XmpTransaction,
    ) -> None:
        self.catalog = catalog
        self.repository = repository
        self.transaction = transaction

    def scan(
        self,
        folder: str | Path,
        direction: str,
        sync_rating: bool,
        sync_label: bool,
        *,
        recursive: bool = False,
        progress: ProgressCallback | None = None,
    ) -> SyncScanResult:
        return plan_sync(
            self.catalog.images(folder, recursive),
            direction,
            sync_rating,
            sync_label,
            self.repository.read,
            progress,
        )

    def execute(
        self,
        operations: list[SyncOperation],
        progress: ProgressCallback | None = None,
    ) -> tuple[int, Path]:
        return self.transaction.execute(operations, progress)

    def undo(self, progress: ProgressCallback | None = None) -> int:
        return self.transaction.undo_latest(progress)

    def has_undo(self) -> bool:
        """只读查询是否有尚未撤回的 XMP 同步记录。"""

        return self.transaction.has_undo()


__all__ = ["XmpSyncUseCase"]
