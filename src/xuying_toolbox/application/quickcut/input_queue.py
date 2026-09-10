"""关键词快切输入队列用例，只编排路径展开与领域过滤。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from xuying_toolbox.domain.ports.quickcut_input import QuickCutInputExpander
from xuying_toolbox.domain.services.input_queue import unique_supported_paths


@dataclass(frozen=True, slots=True)
class InputQueueResult:
    added: list[Path]
    duplicates: int
    ignored: int


class QuickCutInputQueueUseCase:
    def __init__(self, expander: QuickCutInputExpander) -> None:
        self._expander = expander

    def add(
        self,
        inputs: Iterable[str | Path],
        existing: Iterable[Path] = (),
    ) -> InputQueueResult:
        """加入文件或目录，不打开、不解析、不写入任何图片。"""
        candidates, expansion_ignored = self._expander.expand(inputs)
        added, duplicates, filtered_ignored = unique_supported_paths(candidates, existing)
        return InputQueueResult(added, duplicates, expansion_ignored + filtered_ignored)


__all__ = ["InputQueueResult", "QuickCutInputQueueUseCase"]
