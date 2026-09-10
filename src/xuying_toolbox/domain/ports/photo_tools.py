"""照片工具用例依赖的文件、事务与记录端口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from xuying_toolbox.domain.models.photo import RenamePlan, SyncOperation
from xuying_toolbox.domain.services.progress import ProgressCallback
from xuying_toolbox.domain.services.xmp import XmpProperties


class PhotoCatalog(Protocol):
    def images(self, folder: str | Path, recursive: bool) -> list[Path]: ...

    def sidecars(self, image_path: Path) -> list[Path]: ...

    def preferred_sidecar(self, image_path: Path) -> Path: ...

    def exists(self, path: Path) -> bool: ...


class RenameTransaction(Protocol):
    def run(
        self,
        pairs: list[tuple[Path, Path]],
        progress: ProgressCallback | None = None,
    ) -> None: ...


class RenameJournal(Protocol):
    def create(self, plan: RenamePlan) -> Path: ...

    def latest(self) -> Path | None: ...

    def load(self, manifest: Path) -> dict[str, Any]: ...

    def mark_completed(self, manifest: Path) -> None: ...

    def mark_failed(self, manifest: Path, detail: str) -> None: ...

    def delete(self, manifest: Path) -> None: ...


class XmpRepository(Protocol):
    def read(self, path: Path) -> XmpProperties: ...


class XmpTransaction(Protocol):
    def execute(
        self,
        operations: list[SyncOperation],
        progress: ProgressCallback | None = None,
    ) -> tuple[int, Path]: ...

    def undo_latest(self, progress: ProgressCallback | None = None) -> int: ...

    def has_undo(self) -> bool: ...
