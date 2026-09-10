"""ExifRead 元数据适配器。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import exifread


class ExifMetadataReader:
    def capture_time(self, path: Path) -> datetime:
        try:
            with path.open("rb") as file_obj:
                tags = exifread.process_file(
                    file_obj,
                    stop_tag="EXIF DateTimeOriginal",
                    details=False,
                )
            value = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
            if value:
                return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
        except Exception:  # noqa: BLE001
            # 损坏或不支持的照片不能阻断扫描，保持旧版回退语义。
            pass
        return datetime.fromtimestamp(path.stat().st_mtime)
