"""文件夹选择与拖放的共享校验。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl


def local_directory_from_url(folder_url: QUrl) -> tuple[str, str | None]:
    """只接受已存在的本地文件夹，防止把单个文件当成工作目录。"""

    if not folder_url.isValid() or not folder_url.isLocalFile():
        return "", "请拖入一个本地文件夹。"
    value = folder_url.toLocalFile()
    path = Path(value).expanduser()
    if not path.is_dir():
        return "", "请拖入文件夹，不要拖入单个文件。"
    return str(path), None


__all__ = ["local_directory_from_url"]
