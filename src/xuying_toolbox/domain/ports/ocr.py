"""关键词快切 OCR 引擎合同。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from xuying_toolbox.domain.models.quickcut import OCRCandidate


@dataclass(frozen=True, slots=True)
class OCRResult:
    width: int
    height: int
    candidates: tuple[OCRCandidate, ...]


class OCRProvider(Protocol):
    @property
    def available(self) -> bool: ...

    def recognize(self, image_path: Path, keyword: str) -> OCRResult: ...
