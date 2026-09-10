"""照片元数据读取端口。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol


class MetadataReader(Protocol):
    def capture_time(self, path: Path) -> datetime:
        """返回拍摄时间；无法读取 EXIF 时由适配器回退到修改时间。"""

        ...
