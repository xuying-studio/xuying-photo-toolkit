"""本地照片目录实现。"""

from __future__ import annotations

from pathlib import Path

from xuying_toolbox.infrastructure.filesystem.scanner import (
    find_sidecars,
    iter_image_files,
    preferred_sidecar,
)


class LocalPhotoCatalog:
    def images(self, folder: str | Path, recursive: bool) -> list[Path]:
        return iter_image_files(folder, recursive)

    def sidecars(self, image_path: Path) -> list[Path]:
        return find_sidecars(image_path)

    def preferred_sidecar(self, image_path: Path) -> Path:
        return preferred_sidecar(image_path)

    def exists(self, path: Path) -> bool:
        return path.exists()
