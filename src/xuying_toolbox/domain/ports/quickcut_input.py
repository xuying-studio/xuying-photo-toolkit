"""关键词快切本地输入枚举合同。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol


class QuickCutInputExpander(Protocol):
    def expand(self, inputs: Iterable[str | Path]) -> tuple[list[Path], int]: ...
