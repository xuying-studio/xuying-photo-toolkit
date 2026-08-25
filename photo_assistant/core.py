"""三个照片处理功能的共享核心逻辑。

这个模块不依赖图形界面，便于自动化测试，也能确保所有修改操作都先预览、
再备份、后执行。
"""

from __future__ import annotations

import base64
import html
import json
import ntpath
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from xml.etree import ElementTree
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import exifread
from send2trash import send2trash

if sys.platform == "win32":
    import pythoncom as _pythoncom
    import pywintypes as _pywintypes
    from win32com.shell import shell as _win32_shell
    from win32com.shell import shellcon as _win32_shellcon
else:
    _pythoncom = None
    _pywintypes = None
    _win32_shell = None
    _win32_shellcon = None


APP_NAME = "旭影的摄影工具集"
# 保留旧数据目录，确保改名后仍可撤回之前的重命名、清理和 XMP 同步。


def app_data_dir(app_name: str) -> Path:
    """返回当前系统适合保存用户级应用数据的目录。"""

    if sys.platform == "win32":
        roaming = os.environ.get("APPDATA")
        if roaming:
            return Path(roaming) / app_name
        return Path.home() / "AppData" / "Roaming" / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    config_home = os.environ.get("XDG_CONFIG_HOME")
    return (Path(config_home) if config_home else Path.home() / ".config") / app_name


APP_SUPPORT_DIR = app_data_dir("摄影文件后期处理助手")
RENAME_BACKUP_DIR = APP_SUPPORT_DIR / "rename_backups"
XMP_BACKUP_DIR = APP_SUPPORT_DIR / "xmp_backups"
CLEANUP_UNDO_FILE = APP_SUPPORT_DIR / "cleanup_undo.json"
RECOVERY_DIR_NAME = ".摄影文件后期处理助手-恢复备份"

JPG_EXTENSIONS = {".jpg", ".jpeg"}
RAW_EXTENSIONS = {
    ".arw", ".cr2", ".cr3", ".crw", ".nef", ".nrw", ".raf", ".rw2",
    ".orf", ".pef", ".dng", ".x3f", ".3fr", ".fff", ".srw", ".mrw",
    ".mos", ".erf", ".iiq", ".kdc", ".mef", ".raw", ".gpr",
}
IMAGE_EXTENSIONS = JPG_EXTENSIONS | RAW_EXTENSIONS
COUNTER_LEN = 5
RENAMED_STEM_RE = re.compile(
    rf"^DSC(?P<date>\d{{2}}-\d{{2}}-\d{{2}})-(?P<counter>\d{{{COUNTER_LEN}}})$",
    re.IGNORECASE,
)

RE_RATING_ATTR = re.compile(
    rb'(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Rating\s*=\s*["\']\s*'
    rb'([0-5])(?:\.0+)?\s*["\']',
    re.IGNORECASE,
)
RE_RATING_ELEM = re.compile(
    rb'<(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Rating\b[^>]*>\s*'
    rb'([0-5])(?:\.0+)?\s*'
    rb'</(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Rating\s*>',
    re.IGNORECASE,
)
RE_LABEL_ATTR = re.compile(
    rb'(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Label\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)
RE_LABEL_ATTR_SINGLE = re.compile(
    rb"(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Label\s*=\s*'([^']*)'",
    re.IGNORECASE,
)
RE_LABEL_ELEM = re.compile(
    rb'<(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Label\b[^>]*>\s*([^<]*?)\s*'
    rb'</(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Label\s*>',
    re.IGNORECASE,
)
XMP_JPEG_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
XMP_NAMESPACE = "http://ns.adobe.com/xap/1.0/"

ProgressCallback = Callable[[int, int, str], None]


def _report_progress(
    callback: ProgressCallback | None,
    current: int,
    total: int,
    message: str,
) -> None:
    """向界面报告当前进度；未提供回调时保持原有调用方式。"""

    if callback is not None:
        callback(max(0, current), max(0, total), message)


@dataclass(frozen=True)
class RenameOperation:
    """单个文件的重命名动作。"""

    source: str
    target: str
    kind: str


@dataclass
class RenamePlan:
    """重命名预览计划。"""

    operations: list[RenameOperation]
    image_count: int
    conflicts: list[str]
    warnings: list[str]
    stats: "RenameScanStats"


@dataclass(frozen=True)
class RenameScanStats:
    """时间重命名扫描统计。"""

    total_images: int
    raw_count: int
    jpg_count: int
    already_named_count: int
    skipped_count: int
    xmp_count: int


@dataclass(frozen=True)
class CleanupItem:
    """待移入废纸篓的文件。"""

    path: str
    missing_pair_kind: str


@dataclass(frozen=True)
class CleanupScanResult:
    """RAW/JPG 配对清理扫描结果。"""

    items: list[CleanupItem]
    total_images: int
    raw_count: int
    jpg_count: int
    target_count: int
    paired_target_count: int


@dataclass(frozen=True)
class SyncOperation:
    """单个 XMP 同步动作。"""

    source: str
    target: str
    target_is_raw: bool
    rating: int | None
    label: str | None
    old_rating: int
    old_label: str | None


@dataclass(frozen=True)
class SyncScanResult:
    """XMP 标记同步扫描结果。"""

    operations: list[SyncOperation]
    total_images: int
    source_count: int
    target_count: int
    matched_count: int
    marked_count: int
    up_to_date_count: int


@dataclass(frozen=True)
class JpegXmpSegment:
    """JPEG 中标准 XMP APP1 段的位置和 payload。"""

    start: int
    end: int
    payload: bytes


def _ensure_support_dirs() -> None:
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    RENAME_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    XMP_BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _iter_files(folder: str | Path, recursive: bool) -> Iterable[Path]:
    root = Path(folder)
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        if not path.is_file():
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            relative_parts = path.parts
        if any(part.startswith(".") for part in relative_parts):
            continue
        yield path


def iter_image_files(folder: str | Path, recursive: bool = True) -> list[Path]:
    """返回文件夹中的受支持照片，结果稳定排序。"""

    return sorted(
        (p for p in _iter_files(folder, recursive) if p.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: str(p).casefold(),
    )


def extract_original_number(filename: str) -> str | None:
    """从文件名中提取第一段连续数字。"""

    match = re.search(r"(\d+)", Path(filename).stem)
    return match.group(1) if match else None


def get_capture_time(path: str | Path) -> datetime:
    """优先读取 EXIF 拍摄时间，失败时使用文件修改时间。"""

    try:
        with open(path, "rb") as file_obj:
            tags = exifread.process_file(
                file_obj,
                stop_tag="EXIF DateTimeOriginal",
                details=False,
            )
        value = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if value:
            return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(Path(path).stat().st_mtime)


def _find_sidecars(image_path: Path) -> list[Path]:
    """查找标准和旧式命名的 XMP 侧车文件。"""

    wanted = {
        f"{image_path.stem}.xmp".casefold(),
        f"{image_path.name}.xmp".casefold(),
    }
    try:
        return sorted(
            (p for p in image_path.parent.iterdir() if p.is_file() and p.name.casefold() in wanted),
            key=lambda p: (p.name.casefold() != f"{image_path.stem}.xmp".casefold(), p.name.casefold()),
        )
    except OSError:
        return []


def build_rename_plan(
    folder: str | Path,
    recursive: bool = True,
    progress: ProgressCallback | None = None,
) -> RenamePlan:
    """生成照片与对应 XMP 侧车的安全重命名计划。"""

    files = iter_image_files(folder, recursive)
    groups: dict[tuple[str, str], list[Path]] = {}
    capture_times: dict[tuple[str, str], datetime] = {}
    warnings: list[str] = []
    existing_counters: dict[str, int] = {}
    already_named_count = 0
    skipped_count = 0
    total_files = len(files)
    total_steps = total_files * 2 + 1
    _report_progress(progress, 0, total_steps, f"正在读取照片信息 0/{total_files}")

    for index, path in enumerate(files, start=1):
        renamed_match = RENAMED_STEM_RE.match(path.stem)
        if renamed_match:
            already_named_count += 1
            date_text = renamed_match.group("date")
            existing_counters[date_text] = max(
                existing_counters.get(date_text, 0),
                int(renamed_match.group("counter")),
            )
        else:
            number = extract_original_number(path.name)
            if number is None:
                skipped_count += 1
                warnings.append(f"未找到原始编号，已跳过：{path}")
            else:
                key = (str(path.parent).casefold(), number)
                groups.setdefault(key, []).append(path)
                capture_time = get_capture_time(path)
                if key not in capture_times or capture_time < capture_times[key]:
                    capture_times[key] = capture_time
        _report_progress(
            progress,
            index,
            total_steps,
            f"正在读取拍摄时间 {index}/{total_files}",
        )

    ordered_groups: list[tuple[datetime, str, list[Path]]] = []
    for key, members in groups.items():
        ordered_groups.append((capture_times[key], key[1], members))
    ordered_groups.sort(key=lambda item: (item[0], item[1], str(item[2][0]).casefold()))

    operations: list[RenameOperation] = []
    last_date: str | None = None
    counter = 0
    image_count = 0
    planned_files = 0

    _report_progress(
        progress,
        total_files,
        total_steps,
        f"正在生成重命名预览 0/{total_files}",
    )

    for capture_time, _, members in ordered_groups:
        date_text = capture_time.strftime("%y-%m-%d")
        if date_text != last_date:
            last_date = date_text
            counter = existing_counters.get(date_text, 0) + 1
        else:
            counter += 1

        for source in sorted(members, key=lambda p: p.suffix.casefold()):
            target_name = f"DSC{date_text}-{counter:0{COUNTER_LEN}d}{source.suffix.lower()}"
            target = source.with_name(target_name)
            if source != target:
                operations.append(RenameOperation(str(source), str(target), "照片"))
                image_count += 1

            if source.suffix.lower() in RAW_EXTENSIONS:
                sidecars = _find_sidecars(source)
                if len(sidecars) > 1:
                    warnings.append(f"发现多个 XMP 侧车，仅处理优先项：{source}")
                if sidecars:
                    sidecar_source = sidecars[0]
                    sidecar_target = target.with_suffix(".xmp")
                    if sidecar_source != sidecar_target:
                        operations.append(
                            RenameOperation(str(sidecar_source), str(sidecar_target), "XMP 侧车")
                        )
            planned_files += 1
            _report_progress(
                progress,
                total_files + planned_files,
                total_steps,
                f"正在生成重命名预览 {planned_files}/{total_files}",
            )

    conflicts = _find_rename_conflicts(operations)
    stats = RenameScanStats(
        total_images=len(files),
        raw_count=sum(path.suffix.lower() in RAW_EXTENSIONS for path in files),
        jpg_count=sum(path.suffix.lower() in JPG_EXTENSIONS for path in files),
        already_named_count=already_named_count,
        skipped_count=skipped_count,
        xmp_count=sum(operation.kind == "XMP 侧车" for operation in operations),
    )
    _report_progress(progress, total_steps, total_steps, f"扫描完成 {total_files}/{total_files}")
    return RenamePlan(operations, image_count, conflicts, warnings, stats)


def _find_rename_conflicts(operations: list[RenameOperation]) -> list[str]:
    conflicts: list[str] = []
    sources = {Path(op.source) for op in operations}
    targets: dict[Path, int] = {}
    for op in operations:
        target = Path(op.target)
        targets[target] = targets.get(target, 0) + 1
    for target, count in targets.items():
        if count > 1:
            conflicts.append(f"多个文件将被重命名为同一路径：{target}")
        elif target.exists() and target not in sources:
            conflicts.append(f"目标文件已经存在：{target}")
    return conflicts


def _run_two_phase_rename(
    pairs: list[tuple[Path, Path]],
    progress: ProgressCallback | None = None,
) -> None:
    """使用临时文件名完成事务式重命名，失败时尽力回滚。"""

    active = [(source, target) for source, target in pairs if source != target]
    source_set = {source for source, _ in active}
    target_set: set[Path] = set()
    for source, target in active:
        if not source.exists():
            raise FileNotFoundError(f"源文件不存在：{source}")
        if target in target_set:
            raise FileExistsError(f"目标路径重复：{target}")
        target_set.add(target)
        if target.exists() and target not in source_set:
            raise FileExistsError(f"目标文件已经存在：{target}")

    staged: list[tuple[Path, Path, Path]] = []
    completed: list[tuple[Path, Path]] = []
    total_steps = len(active) * 2
    _report_progress(progress, 0, total_steps, f"正在准备文件 0/{len(active)}")
    try:
        for index, (source, target) in enumerate(active, start=1):
            temporary = source.with_name(f".{source.name}.photo-assistant-{uuid.uuid4().hex}.tmp")
            source.rename(temporary)
            staged.append((source, temporary, target))
            _report_progress(
                progress,
                index,
                total_steps,
                f"正在准备文件 {index}/{len(active)} · {source.name}",
            )
        for index, (source, temporary, target) in enumerate(staged, start=1):
            temporary.rename(target)
            completed.append((source, target))
            _report_progress(
                progress,
                len(active) + index,
                total_steps,
                f"正在写入新名称 {index}/{len(active)} · "
                f"{source.name} → {target.name}",
            )
    except Exception:
        for source, target in reversed(completed):
            if target.exists() and not source.exists():
                target.rename(source)
        for source, temporary, _ in reversed(staged):
            if temporary.exists() and not source.exists():
                temporary.rename(source)
        raise


def execute_rename_plan(
    plan: RenamePlan,
    progress: ProgressCallback | None = None,
) -> Path:
    """执行重命名计划，并返回撤回清单路径。"""

    if plan.conflicts:
        raise ValueError("计划存在冲突，不能执行。")
    if not plan.operations:
        raise ValueError("没有需要执行的重命名操作。")
    _ensure_support_dirs()
    backup_path = RENAME_BACKUP_DIR / (
        datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8] + ".json"
    )
    manifest = {
        "created_at": datetime.now().isoformat(),
        "operations": [asdict(op) for op in plan.operations],
    }
    backup_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        _run_two_phase_rename(
            [(Path(op.source), Path(op.target)) for op in plan.operations],
            progress,
        )
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def _latest_json(folder: Path) -> Path | None:
    files = sorted(folder.glob("*.json"), reverse=True) if folder.exists() else []
    return files[0] if files else None


def undo_latest_rename(progress: ProgressCallback | None = None) -> int:
    """撤回最近一次重命名，返回恢复的文件数量。"""

    backup_path = _latest_json(RENAME_BACKUP_DIR)
    if backup_path is None:
        raise FileNotFoundError("没有可撤回的重命名记录。")
    data = json.loads(backup_path.read_text(encoding="utf-8"))
    operations = data.get("operations", [])
    reversed_pairs = [
        (Path(item["target"]), Path(item["source"]))
        for item in operations
    ]
    _run_two_phase_rename(reversed_pairs, progress)
    backup_path.unlink()
    return len(reversed_pairs)


def scan_cleanup(
    folder: str | Path,
    delete_kind: str,
    recursive: bool = True,
    progress: ProgressCallback | None = None,
) -> CleanupScanResult:
    """扫描配对情况并返回待清理项目与统计信息。"""

    delete_kind = delete_kind.upper()
    if delete_kind not in {"JPG", "RAW"}:
        raise ValueError("清理类型必须是 JPG 或 RAW。")
    target_exts = JPG_EXTENSIONS if delete_kind == "JPG" else RAW_EXTENSIONS
    pair_exts = RAW_EXTENSIONS if delete_kind == "JPG" else JPG_EXTENSIONS
    missing_label = "RAW" if delete_kind == "JPG" else "JPG"

    by_folder: dict[Path, dict[str, set[str]]] = {}
    all_files = iter_image_files(folder, recursive)
    total_files = len(all_files)
    total_steps = total_files * 2
    _report_progress(progress, 0, total_steps, f"正在建立照片索引 0/{total_files}")
    for index, path in enumerate(all_files, start=1):
        ext = path.suffix.lower()
        by_folder.setdefault(path.parent, {}).setdefault(path.stem.casefold(), set()).add(ext)
        _report_progress(
            progress,
            index,
            total_steps,
            f"正在建立照片索引 {index}/{total_files}",
        )

    result: list[CleanupItem] = []
    target_count = 0
    for index, path in enumerate(all_files, start=1):
        ext = path.suffix.lower()
        if ext in target_exts:
            target_count += 1
            sibling_exts = by_folder.get(path.parent, {}).get(path.stem.casefold(), set())
            if sibling_exts.isdisjoint(pair_exts):
                result.append(CleanupItem(str(path), missing_label))
        _report_progress(
            progress,
            total_files + index,
            total_steps,
            f"正在检查照片配对 {index}/{total_files}",
        )
    result.sort(key=lambda item: item.path.casefold())
    return CleanupScanResult(
        items=result,
        total_images=len(all_files),
        raw_count=sum(path.suffix.lower() in RAW_EXTENSIONS for path in all_files),
        jpg_count=sum(path.suffix.lower() in JPG_EXTENSIONS for path in all_files),
        target_count=target_count,
        paired_target_count=target_count - len(result),
    )


def build_cleanup_plan(
    folder: str | Path,
    delete_kind: str,
    recursive: bool = True,
    progress: ProgressCallback | None = None,
) -> list[CleanupItem]:
    """兼容旧调用：只返回待清理项目列表。"""

    return scan_cleanup(folder, delete_kind, recursive, progress).items


def move_cleanup_items_to_trash(
    items: list[CleanupItem],
    progress: ProgressCallback | None = None,
) -> tuple[int, list[str]]:
    """将清理项移入系统回收站或废纸篓，并保存可恢复记录。"""

    total_items = len(items)
    trash_name = "回收站" if sys.platform == "win32" else "废纸篓"
    _report_progress(progress, 0, total_items, f"正在准备清理 0/{total_items}")
    if not items:
        return 0, []
    _ensure_support_dirs()
    moved: list[str] = []
    moved_items: list[dict[str, object]] = []
    errors: list[str] = []
    common_root: Path | None = None
    recovery_root: Path | None = None
    if sys.platform != "win32":
        common_root = Path(
            os.path.commonpath([str(Path(item.path).parent) for item in items])
        )
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        recovery_root = common_root / RECOVERY_DIR_NAME / session_id

    for index, item in enumerate(items, start=1):
        recovery_path: Path | None = None
        try:
            source = Path(item.path)
            deleted_at = datetime.now().astimezone().isoformat()
            trash_path: Path | None = None
            source_stat = source.stat()
            recovery_method: str | None = None

            if sys.platform != "win32":
                assert common_root is not None
                assert recovery_root is not None
                trash_dir = _trash_dir_for_path(source)
                relative_path = source.relative_to(common_root)
                recovery_path = recovery_root / relative_path
                recovery_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    # 同卷硬链接不额外占用照片空间，同时保留完整可恢复内容。
                    os.link(source, recovery_path)
                    recovery_method = "hardlink"
                except OSError:
                    # 不支持硬链接的文件系统退回完整复制。
                    shutil.copy2(source, recovery_path)
                    recovery_method = "copy"

            send2trash(item.path)
            moved.append(item.path)
            if sys.platform != "win32":
                trash_path = _find_trashed_file(
                    trash_dir,
                    source_stat.st_dev,
                    source_stat.st_ino,
                    source.name,
                )
            moved_items.append(
                {
                    "original_path": item.path,
                    "deleted_at": deleted_at,
                    "trash_path": str(trash_path) if trash_path else None,
                    "device": source_stat.st_dev,
                    "inode": source_stat.st_ino,
                    "recovery_path": str(recovery_path) if recovery_path else None,
                    "recovery_method": recovery_method,
                }
            )
            _write_cleanup_undo(moved, moved_items)
        except Exception as exc:
            if recovery_path is not None:
                recovery_path.unlink(missing_ok=True)
                _remove_empty_recovery_dirs(recovery_path.parent)
            errors.append(f"{item.path}：{exc}")
        _report_progress(
            progress,
            index,
            total_items,
            f"正在移入{trash_name} {index}/{total_items} · {Path(item.path).name}",
        )
    return len(moved), errors


def _write_cleanup_undo(
    moved_paths: list[str],
    moved_items: list[dict[str, object]],
) -> None:
    """每成功移动一个文件就更新恢复记录，降低中途退出的风险。"""

    payload = {
        "created_at": datetime.now().astimezone().isoformat(),
        "paths": moved_paths,
        "items": moved_items,
    }
    temporary = CLEANUP_UNDO_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(CLEANUP_UNDO_FILE)


def _apple_script_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _mount_point_for_path(path: Path) -> Path:
    """根据设备号找到路径所在卷的挂载点。"""

    current = path if path.exists() else path.parent
    current = current.resolve()
    device = current.stat().st_dev
    while current.parent != current:
        try:
            if current.parent.stat().st_dev != device:
                break
        except OSError:
            break
        current = current.parent
    return current


def _trash_dir_for_path(path: Path) -> Path | None:
    """返回可直接访问的废纸篓目录；Windows 由系统接口管理。"""

    if sys.platform == "win32":
        return None

    mount_point = _mount_point_for_path(path)
    if mount_point == Path("/"):
        return Path.home() / ".Trash"
    return mount_point / ".Trashes" / str(os.getuid())


def _find_trashed_file(
    trash_dir: Path | None,
    device: int | None,
    inode: int | None,
    original_name: str,
) -> Path | None:
    """优先按 inode 找到刚移入废纸篓的真实路径。"""

    if trash_dir is None:
        return None

    exact = trash_dir / original_name
    if exact.exists():
        try:
            stat_result = exact.stat()
            if inode is None or (
                stat_result.st_ino == inode
                and (device is None or stat_result.st_dev == device)
            ):
                return exact
        except OSError:
            pass
    try:
        candidates = list(trash_dir.iterdir())
    except OSError:
        return None
    for candidate in candidates:
        try:
            stat_result = candidate.stat()
        except OSError:
            continue
        if inode is not None and stat_result.st_ino == inode:
            if device is None or stat_result.st_dev == device:
                return candidate
    return None


def _restore_with_finder(original: Path) -> tuple[bool, str | None]:
    """让 Finder 按名称直接恢复，不遍历废纸篓中的其他项目。"""

    filename = _apple_script_escape(original.name)
    parent = _apple_script_escape(str(original.parent))
    script = f'''
tell application "Finder"
    with timeout of 5 seconds
        set targetFolder to POSIX file "{parent}" as alias
        set trashItem to item "{filename}" of trash
        move trashItem to targetFolder
        return "OK"
    end timeout
end tell
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception as exc:
        return False, str(exc)
    if result.returncode == 0 and result.stdout.strip() == "OK":
        return True, None
    detail = result.stderr.strip() or result.stdout.strip() or f"错误码 {result.returncode}"
    return False, detail


def _windows_path_key(value: str | Path) -> str:
    """生成不区分大小写的 Windows 路径比较键。"""

    return ntpath.normcase(ntpath.normpath(str(value)))


def _same_windows_directory(left: str | Path, right: str | Path) -> bool:
    """兼容 Windows 长路径、8.3 短路径和大小写差异。"""

    if _windows_path_key(left) == _windows_path_key(right):
        return True
    try:
        return os.path.samefile(left, right)
    except OSError:
        return False


def _restore_from_windows_recycle_bin(
    original: Path,
    deleted_at: str | None,
) -> tuple[bool, str | None]:
    """通过低层 Windows Shell 接口把回收站项目移回原路径。"""

    if (
        _pythoncom is None
        or _pywintypes is None
        or _win32_shell is None
        or _win32_shellcon is None
    ):
        return False, "Windows 回收站组件不可用。"

    _pythoncom.CoInitialize()
    try:
        recycled_path, find_error = _find_windows_recycled_path(
            original,
            deleted_at,
        )
        if recycled_path is None:
            return False, find_error

        move_error = _move_windows_shell_path(recycled_path, original)
        if move_error is not None:
            return False, move_error
        if original.exists():
            return True, None
        return False, "Windows 已执行还原，但在原位置未检测到文件。"
    except Exception as exc:
        return False, f"Windows 回收站还原失败：{exc}"
    finally:
        _pythoncom.CoUninitialize()


def _find_windows_recycled_path(
    original: Path,
    deleted_at: str | None,
) -> tuple[str | None, str | None]:
    """从回收站 PIDL 中精确找到原路径对应的物理项目。"""

    assert _win32_shell is not None
    assert _win32_shellcon is not None
    assert _pywintypes is not None

    recorded_time: datetime | None = None
    if deleted_at:
        try:
            recorded_time = datetime.fromisoformat(deleted_at).replace(tzinfo=None)
        except ValueError:
            recorded_time = None

    desktop = _win32_shell.SHGetDesktopFolder()
    recycle_pidl = _win32_shell.SHGetSpecialFolderLocation(
        0,
        _win32_shellcon.CSIDL_BITBUCKET,
    )
    recycle_folder = desktop.BindToObject(
        recycle_pidl,
        None,
        _win32_shell.IID_IShellFolder,
    )
    recycle_folder2 = recycle_folder.QueryInterface(
        _win32_shell.IID_IShellFolder2
    )
    enum_flags = (
        _win32_shellcon.SHCONTF_FOLDERS
        | _win32_shellcon.SHCONTF_NONFOLDERS
        | _win32_shellcon.SHCONTF_INCLUDEHIDDEN
    )

    search_deadline = time.monotonic() + 5
    last_observed = 0
    last_errors = 0
    last_name_matches = 0
    last_parent_matches = 0
    while time.monotonic() < search_deadline:
        candidates: list[tuple[float, float, str]] = []
        last_observed = 0
        last_errors = 0
        last_name_matches = 0
        last_parent_matches = 0
        enum_items = recycle_folder.EnumObjects(0, enum_flags)
        while enum_items is not None:
            pidls = enum_items.Next(1)
            if not pidls:
                break
            relative_pidl = pidls[0]
            last_observed += 1
            try:
                deleted_from = str(
                    recycle_folder2.GetDetailsEx(
                        relative_pidl,
                        (_win32_shell.FMTID_Displaced, 2),
                    )
                    or ""
                )
                item_names: set[str] = set()
                property_keys = (
                    (
                        _pywintypes.IID(
                            "{41CF5AE0-F75A-4806-BD87-59C7D9248EB9}"
                        ),
                        100,
                    ),
                    (
                        _pywintypes.IID(
                            "{B725F130-47EF-101A-A5F1-02608C9EEBAC}"
                        ),
                        10,
                    ),
                )
                for property_key in property_keys:
                    try:
                        value = recycle_folder2.GetDetailsEx(
                            relative_pidl,
                            property_key,
                        )
                        if value:
                            item_names.add(str(value))
                    except Exception:
                        continue
                try:
                    display_name = recycle_folder.GetDisplayNameOf(
                        relative_pidl,
                        _win32_shellcon.SHGDN_INFOLDER,
                    )
                    if display_name:
                        item_names.add(str(display_name))
                except Exception:
                    pass
                name_matches = any(
                    _windows_path_key(name)
                    == _windows_path_key(original.name)
                    for name in item_names
                )
                parent_matches = _same_windows_directory(
                    deleted_from,
                    original.parent,
                )
                last_name_matches += int(name_matches)
                last_parent_matches += int(parent_matches)
                if (
                    not name_matches
                    or not parent_matches
                ):
                    continue

                deleted_time: datetime | None = None
                try:
                    deleted_value = recycle_folder2.GetDetailsEx(
                        relative_pidl,
                        (_win32_shell.FMTID_Displaced, 3),
                    )
                    if isinstance(deleted_value, datetime):
                        deleted_time = deleted_value.replace(tzinfo=None)
                except Exception:
                    # 删除时间只用于区分同一路径的多个版本，缺失时仍可恢复。
                    deleted_time = None
                distance = (
                    abs((deleted_time - recorded_time).total_seconds())
                    if deleted_time is not None and recorded_time is not None
                    else float("inf")
                )
                recency = (
                    -deleted_time.timestamp() if deleted_time is not None else 0.0
                )
                recycled_path = str(
                    recycle_folder.GetDisplayNameOf(
                        relative_pidl,
                        _win32_shellcon.SHGDN_FORPARSING,
                    )
                )
                candidates.append((distance, recency, recycled_path))
            except Exception:
                last_errors += 1

        if candidates:
            matched = min(candidates, key=lambda value: (value[0], value[1]))
            return matched[2], None
        time.sleep(0.2)

    return (
        None,
        "Windows 回收站中未找到对应文件，可能已被清空或手动处理。"
        f"（检查 {last_observed} 项，文件名匹配 {last_name_matches} 项，"
        f"原目录匹配 {last_parent_matches} 项，属性读取失败 {last_errors} 项）",
    )


def _move_windows_shell_path(source: str | Path, target: str | Path) -> str | None:
    """使用 SHFileOperation 移动回收站物理项目并检查返回状态。"""

    assert _win32_shell is not None
    assert _win32_shellcon is not None

    flags = (
        _win32_shellcon.FOF_NOCONFIRMATION
        | _win32_shellcon.FOF_NOERRORUI
        | _win32_shellcon.FOF_SILENT
    )
    operation_result = _win32_shell.SHFileOperation(
        (
            0,
            _win32_shellcon.FO_MOVE,
            str(source),
            str(target),
            flags,
            None,
            None,
        )
    )
    result = operation_result[0]
    aborted = operation_result[1]
    if result:
        return f"Windows Shell 移动失败，错误码 {result}。"
    if aborted:
        return "Windows Shell 取消了还原操作。"
    return None


def _restore_with_platform_fallback(
    original: Path,
    record: dict[str, object],
) -> tuple[bool, str | None]:
    """使用当前系统提供的回收站恢复方式。"""

    if sys.platform == "darwin":
        return _restore_with_finder(original)
    if sys.platform == "win32":
        return _restore_from_windows_recycle_bin(
            original,
            str(record.get("deleted_at")) if record.get("deleted_at") else None,
        )
    return False, "请从系统回收站手动还原该文件。"


def _remove_empty_recovery_dirs(start: Path) -> None:
    """只删除已经为空的恢复目录，遇到非空目录立即停止。"""

    current = start
    while current.name:
        is_recovery_root = current.name == RECOVERY_DIR_NAME
        try:
            current.rmdir()
        except OSError:
            break
        if is_recovery_root:
            break
        current = current.parent


def restore_latest_cleanup(
    progress: ProgressCallback | None = None,
) -> tuple[int, list[str]]:
    """恢复最近一次移入系统回收站或废纸篓的文件。"""

    if not CLEANUP_UNDO_FILE.exists():
        raise FileNotFoundError("没有可恢复的清理记录。")
    data = json.loads(CLEANUP_UNDO_FILE.read_text(encoding="utf-8"))
    stored_items = data.get("items")
    if stored_items:
        records = stored_items
    else:
        # 兼容 1.0.0 保存的旧格式。
        records = [{"original_path": path} for path in data.get("paths", [])]
    restored = 0
    errors: list[str] = []
    total_records = len(records)
    _report_progress(progress, 0, total_records, f"正在准备恢复 0/{total_records}")

    for index, record in enumerate(records, start=1):
        original = Path(record["original_path"])
        if original.exists():
            errors.append(f"原位置已有同名文件，未覆盖：{original.name}")
            _report_progress(
                progress,
                index,
                total_records,
                f"跳过恢复 {index}/{total_records} · {original.name}",
            )
            continue
        if not original.parent.is_dir():
            errors.append(f"原文件夹不存在：{original.parent}")
            _report_progress(
                progress,
                index,
                total_records,
                f"恢复失败 {index}/{total_records} · {original.name}",
            )
            continue

        recovery_path_value = record.get("recovery_path")
        recovery_path = Path(recovery_path_value) if recovery_path_value else None
        if recovery_path is not None and recovery_path.exists():
            try:
                shutil.move(str(recovery_path), str(original))
                _remove_empty_recovery_dirs(recovery_path.parent)
                restored += 1
                _report_progress(
                    progress,
                    index,
                    total_records,
                    f"已恢复文件 {index}/{total_records} · {original.name}",
                )
                continue
            except Exception as exc:
                errors.append(f"{original.name}：安全备份恢复失败：{exc}")
                _report_progress(
                    progress,
                    index,
                    total_records,
                    f"恢复失败 {index}/{total_records} · {original.name}",
                )
                continue

        trash_path_value = record.get("trash_path")
        trash_path = Path(trash_path_value) if trash_path_value else None
        if trash_path is None or not trash_path.exists():
            try:
                trash_path = _find_trashed_file(
                    _trash_dir_for_path(original),
                    record.get("device"),
                    record.get("inode"),
                    original.name,
                )
            except OSError:
                trash_path = None

        if trash_path is not None and trash_path.exists():
            try:
                shutil.move(str(trash_path), str(original))
                restored += 1
                _report_progress(
                    progress,
                    index,
                    total_records,
                    f"已恢复文件 {index}/{total_records} · {original.name}",
                )
                continue
            except Exception:
                # 直接访问可能被 macOS 隐私权限阻止，继续交给 Finder。
                pass

        succeeded, detail = _restore_with_platform_fallback(original, record)
        if succeeded:
            restored += 1
        else:
            errors.append(f"{original.name}：{detail}")
        _report_progress(
            progress,
            index,
            total_records,
            (
                f"已恢复文件 {index}/{total_records} · {original.name}"
                if succeeded
                else f"恢复失败 {index}/{total_records} · {original.name}"
            ),
        )

    if restored == len(records):
        CLEANUP_UNDO_FILE.unlink(missing_ok=True)
    else:
        # 只保留尚未恢复的记录，避免再次恢复已成功的文件。
        remaining = [
            record
            for record in records
            if not Path(record["original_path"]).exists()
        ]
        data["items"] = remaining
        data["paths"] = [record["original_path"] for record in remaining]
        try:
            CLEANUP_UNDO_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
    return restored, errors


def _read_bytes(path: str | Path) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except (OSError, PermissionError):
        return None


def _find_jpeg_xmp_segment(content: bytes) -> JpegXmpSegment | None:
    """解析 JPEG metadata markers，返回标准 XMP APP1 段。"""

    if not content.startswith(b"\xff\xd8"):
        return None
    position = 2
    content_length = len(content)
    while position < content_length:
        if content[position] != 0xFF:
            return None
        while position < content_length and content[position] == 0xFF:
            position += 1
        if position >= content_length:
            return None
        marker = content[position]
        segment_start = position - 1
        position += 1

        if marker in {0xD9, 0xDA}:
            return None
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if position + 2 > content_length:
            return None
        segment_length = int.from_bytes(content[position:position + 2], "big")
        if segment_length < 2:
            return None
        segment_end = position + segment_length
        if segment_end > content_length:
            return None
        payload = content[position + 2:segment_end]
        if marker == 0xE1 and payload.startswith(XMP_JPEG_HEADER):
            return JpegXmpSegment(segment_start, segment_end, payload)
        position = segment_end
    return None


def _read_jpeg_xmp_payload(path: str | Path) -> bytes | None:
    """只读取 JPEG metadata 区域中的 XMP，不加载压缩图像数据。"""

    try:
        with Path(path).open("rb") as file_obj:
            if file_obj.read(2) != b"\xff\xd8":
                return None
            while True:
                marker_prefix = file_obj.read(1)
                if not marker_prefix:
                    return None
                if marker_prefix != b"\xff":
                    return None
                marker_byte = file_obj.read(1)
                while marker_byte == b"\xff":
                    marker_byte = file_obj.read(1)
                if not marker_byte:
                    return None
                marker = marker_byte[0]
                if marker in {0xD9, 0xDA}:
                    return None
                if marker == 0x01 or 0xD0 <= marker <= 0xD8:
                    continue

                length_bytes = file_obj.read(2)
                if len(length_bytes) != 2:
                    return None
                segment_length = int.from_bytes(length_bytes, "big")
                if segment_length < 2:
                    return None
                payload_length = segment_length - 2
                if marker == 0xE1:
                    payload = file_obj.read(payload_length)
                    if len(payload) != payload_length:
                        return None
                    if payload.startswith(XMP_JPEG_HEADER):
                        return payload
                else:
                    file_obj.seek(payload_length, os.SEEK_CUR)
    except (OSError, PermissionError):
        return None


def _replace_jpeg_xmp_segment(
    content: bytes,
    segment: JpegXmpSegment,
    payload: bytes,
) -> bytes:
    """重建 XMP APP1 并同步更新 JPEG segment length。"""

    segment_length = len(payload) + 2
    if segment_length > 65535:
        raise ValueError("XMP 数据过大，无法写入 JPG。")
    replacement = (
        b"\xff\xe1"
        + segment_length.to_bytes(2, "big")
        + payload
    )
    return content[:segment.start] + replacement + content[segment.end:]


def _is_raw(path: str | Path) -> bool:
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def _preferred_sidecar(path: str | Path) -> Path:
    image = Path(path)
    sidecars = _find_sidecars(image)
    if not sidecars:
        return image.with_suffix(".xmp")

    standard_name = f"{image.stem}.xmp".casefold()

    def sidecar_priority(sidecar: Path) -> tuple[int, int]:
        try:
            modified = sidecar.stat().st_mtime_ns
        except OSError:
            modified = -1
        return modified, int(sidecar.name.casefold() == standard_name)

    return max(sidecars, key=sidecar_priority)


def _read_xml_xmp_value(content: bytes | None, property_name: str) -> str | None:
    """按 Adobe XMP namespace 读取属性或元素，不依赖前缀名称。"""

    if not content:
        return None
    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, ValueError):
        return None

    qualified_name = f"{{{XMP_NAMESPACE}}}{property_name}"
    for element in root.iter():
        attribute_value = element.attrib.get(qualified_name)
        if attribute_value is not None:
            return attribute_value
        if element.tag == qualified_name and element.text is not None:
            return element.text
    return None


def _xmp_namespace_prefix(content: bytes | None) -> bytes | None:
    """返回绑定到 Adobe XMP namespace 的实际前缀，例如 xmp 或 xap。"""

    if not content:
        return None
    pattern = re.compile(
        rb"xmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*(['\"])"
        + re.escape(XMP_NAMESPACE.encode("ascii"))
        + rb"\2",
        re.IGNORECASE,
    )
    match = pattern.search(content)
    return match.group(1) if match else None


def _parse_rating_value(value: str | None) -> int:
    """把 XMP 星标文本规范化为 0～5，无法识别时返回 0。"""

    if value is None:
        return 0
    match = re.fullmatch(r"\s*([0-5])(?:\.0+)?\s*", value)
    return int(match.group(1)) if match else 0


def _read_rating(content: bytes | None) -> int:
    if not content:
        return 0
    xml_rating = _read_xml_xmp_value(content, "Rating")
    if xml_rating is not None:
        return _parse_rating_value(xml_rating)
    match = RE_RATING_ATTR.search(content) or RE_RATING_ELEM.search(content)
    return int(match.group(1)) if match else 0


def _read_label(content: bytes | None) -> str | None:
    if not content:
        return None
    xml_label = _read_xml_xmp_value(content, "Label")
    if xml_label is not None:
        return xml_label or None
    match = (
        RE_LABEL_ATTR.search(content)
        or RE_LABEL_ATTR_SINGLE.search(content)
        or RE_LABEL_ELEM.search(content)
    )
    if not match:
        return None
    value = match.group(1).decode("utf-8", errors="replace")
    return html.unescape(value) or None


def read_xmp_properties(path: str | Path) -> tuple[int, str | None]:
    """读取 RAW 侧车或 JPG 内嵌 XMP 的星标与颜色标签。"""

    content = (
        _read_bytes(_preferred_sidecar(path))
        if _is_raw(path)
        else _read_jpeg_xmp_payload(path)
    )
    return _read_rating(content), _read_label(content)


def _pair_for(path: Path, target_exts: set[str]) -> Path | None:
    try:
        candidates = [
            candidate
            for candidate in path.parent.iterdir()
            if candidate.is_file()
            and candidate.stem.casefold() == path.stem.casefold()
            and candidate.suffix.lower() in target_exts
        ]
    except OSError:
        return None
    return sorted(candidates, key=lambda p: p.suffix.casefold())[0] if candidates else None


def _build_pair_index(
    files: list[Path],
    target_exts: set[str],
) -> dict[tuple[str, str], Path]:
    """一次建立同目录同主文件名索引，避免为每张照片重复遍历目录。"""

    candidates: dict[tuple[str, str], list[Path]] = {}
    for path in files:
        if path.suffix.lower() not in target_exts:
            continue
        key = (str(path.parent).casefold(), path.stem.casefold())
        candidates.setdefault(key, []).append(path)
    return {
        key: sorted(paths, key=lambda path: path.suffix.casefold())[0]
        for key, paths in candidates.items()
    }


def scan_sync(
    folder: str | Path,
    direction: str,
    sync_rating: bool,
    sync_label: bool,
    recursive: bool = True,
    progress: ProgressCallback | None = None,
) -> SyncScanResult:
    """扫描 XMP 标记并返回同步计划与统计信息。"""

    if not sync_rating and not sync_label:
        raise ValueError("至少选择一种同步内容。")
    if direction not in {"JPG → RAW", "RAW → JPG"}:
        raise ValueError("同步方向无效。")

    source_exts = JPG_EXTENSIONS if direction == "JPG → RAW" else RAW_EXTENSIONS
    target_exts = RAW_EXTENSIONS if direction == "JPG → RAW" else JPG_EXTENSIONS
    target_is_raw = direction == "JPG → RAW"
    result: list[SyncOperation] = []
    files = iter_image_files(folder, recursive)
    sources = [path for path in files if path.suffix.lower() in source_exts]
    pair_index = _build_pair_index(files, target_exts)
    source_count = len(sources)
    target_count = sum(path.suffix.lower() in target_exts for path in files)
    matched_count = 0
    marked_count = 0
    up_to_date_count = 0
    _report_progress(progress, 0, source_count, f"正在读取 XMP 标记 0/{source_count}")

    for index, source in enumerate(sources, start=1):
        target = pair_index.get(
            (str(source.parent).casefold(), source.stem.casefold())
        )
        if target is not None:
            matched_count += 1
            rating, label = read_xmp_properties(source)
            if (sync_rating and rating > 0) or (sync_label and label):
                marked_count += 1
                old_rating, old_label = read_xmp_properties(target)
                new_rating = rating if sync_rating and rating > 0 else None
                new_label = label if sync_label and label else None
                rating_changed = new_rating is not None and new_rating != old_rating
                label_changed = new_label is not None and new_label != old_label
                if rating_changed or label_changed:
                    result.append(
                        SyncOperation(
                            str(source),
                            str(target),
                            target_is_raw,
                            new_rating,
                            new_label,
                            old_rating,
                            old_label,
                        )
                    )
                else:
                    up_to_date_count += 1
        _report_progress(
            progress,
            index,
            source_count,
            f"正在读取 XMP 标记 {index}/{source_count}",
        )
    return SyncScanResult(
        operations=result,
        total_images=len(files),
        source_count=source_count,
        target_count=target_count,
        matched_count=matched_count,
        marked_count=marked_count,
        up_to_date_count=up_to_date_count,
    )


def build_sync_plan(
    folder: str | Path,
    direction: str,
    sync_rating: bool,
    sync_label: bool,
    recursive: bool = True,
    progress: ProgressCallback | None = None,
) -> list[SyncOperation]:
    """兼容旧调用：只返回待同步操作列表。"""

    return scan_sync(
        folder,
        direction,
        sync_rating,
        sync_label,
        recursive,
        progress,
    ).operations


def _replace_or_insert_property(
    content: bytes,
    property_name: str,
    value: str,
) -> tuple[bytes, bool]:
    escaped = html.escape(value, quote=True).encode("utf-8")
    if property_name == "Rating":
        patterns = (RE_RATING_ATTR, RE_RATING_ELEM)
    else:
        patterns = (RE_LABEL_ATTR, RE_LABEL_ATTR_SINGLE, RE_LABEL_ELEM)

    for pattern in patterns:
        match = pattern.search(content)
        if match:
            if match.group(1) == escaped:
                return content, False
            return content[:match.start(1)] + escaped + content[match.end(1):], True

    prefix = _xmp_namespace_prefix(content)
    if prefix is None:
        return content, False
    start = content.find(b"<rdf:Description")
    if start < 0:
        return content, False
    tag_end = content.find(b">", start)
    if tag_end < 0:
        return content, False
    element_name = prefix + b":" + property_name.encode()
    element = b"\n   <" + element_name + b">" + escaped + b"</" + element_name + b">"
    if content[tag_end - 1:tag_end] == b"/":
        opening = content[start:tag_end - 1] + b">"
        replacement = opening + element + b"\n  </rdf:Description>"
        return content[:start] + replacement + content[tag_end + 1:], True
    return content[:tag_end + 1] + element + content[tag_end + 1:], True


def _make_xmp_xml(rating: int | None, label: str | None) -> bytes:
    rating_element = f"\n   <xmp:Rating>{rating}</xmp:Rating>" if rating is not None else ""
    label_element = (
        f"\n   <xmp:Label>{html.escape(label)}</xmp:Label>" if label is not None else ""
    )
    xml = f'''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">{rating_element}{label_element}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
    return xml.encode("utf-8")


def _insert_jpeg_xmp(content: bytes, rating: int | None, label: str | None) -> bytes:
    if not content.startswith(b"\xff\xd8"):
        raise ValueError("目标 JPG 文件头无效，已停止写入。")
    payload = XMP_JPEG_HEADER + _make_xmp_xml(rating, label)
    segment_length = len(payload) + 2
    if segment_length > 65535:
        raise ValueError("XMP 数据过大，无法写入 JPG。")
    segment = b"\xff\xe1" + segment_length.to_bytes(2, "big") + payload
    return content[:2] + segment + content[2:]


def _write_properties(path: Path, rating: int | None, label: str | None) -> None:
    """写入属性；RAW 只写侧车，JPG 写入内嵌 XMP。"""

    if _is_raw(path):
        sidecar = _preferred_sidecar(path)
        existing = _read_bytes(sidecar)
        if existing is None:
            sidecar.write_bytes(_make_xmp_xml(rating, label))
            return
        updated = existing
        changed = False
        if rating is not None:
            updated, did_change = _replace_or_insert_property(updated, "Rating", str(rating))
            changed = changed or did_change
        if label is not None:
            updated, did_change = _replace_or_insert_property(updated, "Label", label)
            changed = changed or did_change
        if not changed and _xmp_namespace_prefix(existing) is None:
            updated = _make_xmp_xml(rating, label)
            changed = True
        if changed:
            sidecar.write_bytes(updated)
        actual_rating, actual_label = read_xmp_properties(path)
        if rating is not None and actual_rating != rating:
            raise ValueError("RAW 侧车星标写入后校验失败。")
        if label is not None and actual_label != label:
            raise ValueError("RAW 侧车颜色标签写入后校验失败。")
        return

    existing = path.read_bytes()
    updated = existing
    changed = False
    xmp_segment = _find_jpeg_xmp_segment(existing)
    if xmp_segment is None:
        updated = _insert_jpeg_xmp(existing, rating, label)
        changed = True
    else:
        xmp_payload = xmp_segment.payload
        if _xmp_namespace_prefix(xmp_payload) is None:
            raise ValueError("JPG 已有 XMP 包，但无法识别 Adobe XMP namespace。")
        updated_payload = xmp_payload
        if rating is not None:
            updated_payload, did_change = _replace_or_insert_property(
                updated_payload,
                "Rating",
                str(rating),
            )
            changed = changed or did_change
        if label is not None:
            updated_payload, did_change = _replace_or_insert_property(
                updated_payload,
                "Label",
                label,
            )
            changed = changed or did_change
        if changed:
            updated = _replace_jpeg_xmp_segment(
                existing,
                xmp_segment,
                updated_payload,
            )
    if changed:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_bytes(updated)
        shutil.copystat(path, temporary)
        temporary.replace(path)
    actual_rating, actual_label = read_xmp_properties(path)
    if rating is not None and actual_rating != rating:
        raise ValueError("JPG 星标写入后校验失败。")
    if label is not None and actual_label != label:
        raise ValueError("JPG 颜色标签写入后校验失败。")


def execute_sync_plan(
    operations: list[SyncOperation],
    progress: ProgressCallback | None = None,
) -> tuple[int, Path]:
    """备份目标文件后执行 XMP 同步。"""

    if not operations:
        raise ValueError("没有需要同步的项目。")
    _ensure_support_dirs()
    session_dir = XMP_BACKUP_DIR / (
        datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    )
    session_dir.mkdir(parents=True)
    manifest_entries: list[dict] = []
    total_operations = len(operations)
    total_steps = total_operations * 2
    _report_progress(progress, 0, total_steps, f"正在备份目标文件 0/{total_operations}")

    for index, operation in enumerate(operations):
        target = Path(operation.target)
        entry: dict[str, object] = {
            "target": str(target),
            "target_is_raw": operation.target_is_raw,
        }
        if operation.target_is_raw:
            sidecar = _preferred_sidecar(target)
            entry["sidecar"] = str(sidecar)
            entry["sidecar_existed"] = sidecar.exists()
            if sidecar.exists():
                backup_name = f"{index:05d}_{sidecar.name}.bak"
                shutil.copy2(sidecar, session_dir / backup_name)
                entry["backup_name"] = backup_name
        else:
            backup_name = f"{index:05d}_{target.name}.bak"
            backup_path = session_dir / backup_name
            try:
                # JPG 通过临时文件 replace 写入；同卷硬链接可瞬间保留旧 inode。
                os.link(target, backup_path)
                entry["backup_method"] = "hardlink"
            except OSError:
                shutil.copy2(target, backup_path)
                entry["backup_method"] = "copy"
            entry["backup_name"] = backup_name
        manifest_entries.append(entry)
        _report_progress(
            progress,
            index + 1,
            total_steps,
            f"正在备份目标文件 {index + 1}/{total_operations} · {target.name}",
        )

    manifest_path = session_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now().isoformat(),
                "undone_at": None,
                "entries": manifest_entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    succeeded = 0
    try:
        for index, operation in enumerate(operations, start=1):
            _write_properties(Path(operation.target), operation.rating, operation.label)
            succeeded += 1
            _report_progress(
                progress,
                total_operations + index,
                total_steps,
                f"正在写入 XMP 标记 {index}/{total_operations} · "
                f"{Path(operation.target).name}",
            )
    except Exception:
        # 任一文件失败时立即恢复本批次，避免留下半完成状态。
        _restore_sync_manifest(manifest_path, mark_undone=True)
        raise
    return succeeded, manifest_path


def _latest_active_sync_manifest() -> Path | None:
    if not XMP_BACKUP_DIR.exists():
        return None
    for manifest in sorted(XMP_BACKUP_DIR.glob("*/manifest.json"), reverse=True):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not data.get("undone_at"):
            return manifest
    return None


def undo_latest_sync(progress: ProgressCallback | None = None) -> int:
    """从完整备份中恢复最近一次 XMP 同步。"""

    manifest_path = _latest_active_sync_manifest()
    if manifest_path is None:
        raise FileNotFoundError("没有可撤回的同步记录。")
    return _restore_sync_manifest(manifest_path, mark_undone=True, progress=progress)


def _restore_sync_manifest(
    manifest_path: Path,
    mark_undone: bool,
    progress: ProgressCallback | None = None,
) -> int:
    """按清单恢复一次同步使用的完整备份。"""

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    restored = 0
    total_entries = len(entries)
    _report_progress(progress, 0, total_entries, f"正在恢复 XMP 备份 0/{total_entries}")
    for index, entry in enumerate(entries, start=1):
        target = Path(entry["target"])
        backup_name = entry.get("backup_name")
        if entry.get("target_is_raw"):
            sidecar = Path(entry["sidecar"])
            if entry.get("sidecar_existed") and backup_name:
                shutil.copy2(manifest_path.parent / str(backup_name), sidecar)
            elif not entry.get("sidecar_existed"):
                sidecar.unlink(missing_ok=True)
            restored += 1
        elif backup_name:
            shutil.copy2(manifest_path.parent / str(backup_name), target)
            restored += 1
        _report_progress(
            progress,
            index,
            total_entries,
            f"正在恢复 XMP 备份 {index}/{total_entries} · {target.name}",
        )
    if mark_undone:
        data["undone_at"] = datetime.now().isoformat()
        manifest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return restored


def describe_label(label: str | None) -> str:
    """将空标签转换为适合界面显示的文本。"""

    return label if label else "无"
