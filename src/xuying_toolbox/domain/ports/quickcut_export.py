"""关键词快切渲染与导出合同。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xuying_toolbox.domain.models.quickcut import NormalizedRect, ProjectSettings
from xuying_toolbox.domain.services.progress import ProgressCallback


@dataclass(frozen=True, slots=True)
class QuickCutExportSource:
    path: Path
    source_box: NormalizedRect | None


@dataclass(frozen=True, slots=True)
class QuickCutExportResult:
    directory: Path
    files: tuple[Path, ...]
    total_frames: int


class QuickCutExportProvider(Protocol):
    def export(
        self,
        sources: tuple[QuickCutExportSource, ...],
        settings: ProjectSettings,
        destination: Path,
        progress: ProgressCallback,
    ) -> QuickCutExportResult: ...
