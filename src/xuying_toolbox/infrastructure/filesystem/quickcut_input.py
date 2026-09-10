"""关键词快切输入的本地路径枚举，不读取图片内容。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def expand_input_paths(inputs: Iterable[str | Path]) -> tuple[list[Path], int]:
    """展开文件和目录；目录只读取直接子项，返回候选与忽略数量。"""
    candidates: list[Path] = []
    ignored = 0
    for value in inputs:
        path = Path(value).expanduser()
        if path.name.startswith("."):
            ignored += 1
            continue
        if path.is_symlink():
            ignored += 1
        elif path.is_dir():
            try:
                children = list(path.iterdir())
            except OSError:
                ignored += 1
                continue
            candidates.extend(children)
        else:
            candidates.append(path)
    return candidates, ignored


class LocalQuickCutInputExpander:
    def expand(self, inputs: Iterable[str | Path]) -> tuple[list[Path], int]:
        return expand_input_paths(inputs)


__all__ = ["LocalQuickCutInputExpander", "expand_input_paths"]
