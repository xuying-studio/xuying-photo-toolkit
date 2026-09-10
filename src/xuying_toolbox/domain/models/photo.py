"""三个照片工具共享的纯 Python 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

JPG_EXTENSIONS = frozenset({".jpg", ".jpeg"})
RAW_EXTENSIONS = frozenset(
    {
        ".arw",
        ".cr2",
        ".cr3",
        ".crw",
        ".nef",
        ".nrw",
        ".raf",
        ".rw2",
        ".orf",
        ".pef",
        ".dng",
        ".x3f",
        ".3fr",
        ".fff",
        ".srw",
        ".mrw",
        ".mos",
        ".erf",
        ".iiq",
        ".kdc",
        ".mef",
        ".raw",
        ".gpr",
    }
)
IMAGE_EXTENSIONS = JPG_EXTENSIONS | RAW_EXTENSIONS
RECOVERY_DIR_NAME = ".摄影文件后期处理助手-恢复备份"


@dataclass(frozen=True, slots=True)
class RenameOperation:
    source: str
    target: str
    kind: str


@dataclass(frozen=True, slots=True)
class RenameScanStats:
    total_images: int
    raw_count: int
    jpg_count: int
    already_named_count: int
    skipped_count: int
    xmp_count: int


@dataclass(slots=True)
class RenamePlan:
    operations: list[RenameOperation]
    image_count: int
    conflicts: list[str]
    warnings: list[str]
    stats: RenameScanStats


@dataclass(frozen=True, slots=True)
class CleanupItem:
    path: str
    missing_pair_kind: str


@dataclass(frozen=True, slots=True)
class CleanupScanResult:
    items: list[CleanupItem]
    total_images: int
    raw_count: int
    jpg_count: int
    target_count: int
    paired_target_count: int


@dataclass(frozen=True, slots=True)
class SyncOperation:
    source: str
    target: str
    target_is_raw: bool
    rating: int | None
    label: str | None
    old_rating: int
    old_label: str | None


@dataclass(frozen=True, slots=True)
class SyncScanResult:
    operations: list[SyncOperation]
    total_images: int
    source_count: int
    target_count: int
    matched_count: int
    marked_count: int
    up_to_date_count: int


@dataclass(frozen=True, slots=True)
class JpegXmpSegment:
    start: int
    end: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class TrashRecord:
    original_path: str
    deleted_at: str
    trash_path: str | None = None
    device: int | None = None
    inode: int | None = None
    recovery_path: str | None = None
    recovery_method: str | None = None


def path_key(path: str | Path) -> str:
    """生成同目录匹配使用的大小写不敏感键。"""

    return str(Path(path)).casefold()
