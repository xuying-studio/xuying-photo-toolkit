"""配对清理用例：扫描必须先于执行，平台动作由适配器提供。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from xuying_toolbox.domain.models.photo import CleanupItem, CleanupScanResult
from xuying_toolbox.domain.ports.photo_tools import PhotoCatalog
from xuying_toolbox.domain.services.cleanup import scan_cleanup
from xuying_toolbox.domain.services.progress import ProgressCallback


class CleanupAdapter(Protocol):
    def move(
        self,
        items: list[CleanupItem],
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]: ...

    def restore(
        self,
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]: ...

    def has_restore(self) -> bool: ...


class CleanupUseCase:
    """编排扫描、确认后的执行和最近一次恢复。"""

    def __init__(self, catalog: PhotoCatalog, adapter: CleanupAdapter) -> None:
        self.catalog = catalog
        self.adapter = adapter
        self._preview: CleanupScanResult | None = None

    def scan(
        self,
        folder: str | Path,
        delete_kind: str,
        *,
        recursive: bool = False,
        progress: ProgressCallback | None = None,
    ) -> CleanupScanResult:
        # 新扫描一开始就废弃旧预览，避免扫描失败后误执行上一批文件。
        self._preview = None
        files = self.catalog.images(folder, recursive)
        self._preview = scan_cleanup(files, delete_kind, progress)
        return self._preview

    def execute(
        self,
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]:
        if self._preview is None:
            raise RuntimeError("必须先扫描并预览，再执行清理。")
        result = self.adapter.move(self._preview.items, progress)
        self._preview = None
        return result

    def restore(
        self,
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]:
        return self.adapter.restore(progress)

    def has_restore(self) -> bool:
        """只读查询是否有待恢复的清理记录。"""

        return self.adapter.has_restore()


__all__ = ["CleanupUseCase"]
