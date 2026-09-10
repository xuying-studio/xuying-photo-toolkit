"""不依赖界面的进度回调约定。"""

from __future__ import annotations

from collections.abc import Callable

ProgressCallback = Callable[[int, int, str], None]


def report_progress(
    callback: ProgressCallback | None,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is not None:
        callback(max(0, current), max(0, total), message)
