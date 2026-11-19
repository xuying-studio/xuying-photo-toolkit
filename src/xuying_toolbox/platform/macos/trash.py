"""macOS 废纸篓适配器：废纸篓是清理文件的唯一来源，撤回仅从废纸篓还原。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

from send2trash import send2trash

from xuying_toolbox.domain.models.photo import CleanupItem, TrashRecord
from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


def _apple_script_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def restore_with_finder(
    original: Path,
    _record: dict[str, object],
) -> tuple[bool, str | None]:
    """让 Finder 按准确文件名恢复，不枚举整个废纸篓。"""

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
    # 系统脚本异常必须转换为可恢复错误，不能让恢复记录丢失。
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if result.returncode == 0 and result.stdout.strip() == "OK":
        return True, None
    detail = result.stderr.strip() or result.stdout.strip() or f"错误码 {result.returncode}"
    return False, detail


def _mount_point_for_path(path: Path) -> Path:
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


def _trash_dir_for_path(path: Path) -> Path:
    mount_point = _mount_point_for_path(path)
    if mount_point == Path("/"):
        return Path.home() / ".Trash"
    return mount_point / ".Trashes" / str(os.getuid())


def locate_trashed_file(
    original: Path,
    device: int | None,
    inode: int | None,
) -> Path | None:
    """优先按名称，再按 inode 定位同一卷的废纸篓项目。"""

    trash_dir = _trash_dir_for_path(original)
    exact = trash_dir / original.name
    if exact.exists():
        try:
            stat = exact.stat()
            if inode is None or (
                stat.st_ino == inode and (device is None or stat.st_dev == device)
            ):
                return exact
        except OSError:
            pass
    try:
        candidates = trash_dir.iterdir()
    except OSError:
        return None
    for candidate in candidates:
        try:
            stat = candidate.stat()
        except OSError:
            continue
        if inode is not None and stat.st_ino == inode:
            if device is None or stat.st_dev == device:
                return candidate
    return None


class MacTrashAdapter:
    """可注入废纸篓操作的 macOS 清理适配器。"""

    def __init__(
        self,
        paths: SupportPaths,
        *,
        send_to_trash: Callable[[str], str | Path | None] = send2trash,
        restore_fallback: Callable[
            [Path, dict[str, object]], tuple[bool, str | None]
        ] = restore_with_finder,
        trash_locator: Callable[[Path, int | None, int | None], Path | None] | None = None,
    ) -> None:
        self.paths = paths
        self._send_to_trash = send_to_trash
        self._restore_fallback = restore_fallback
        self._trash_locator = trash_locator

    def move(
        self,
        items: Iterable[CleanupItem],
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]:
        items = list(items)
        report_progress(progress, 0, len(items), f"正在准备清理 0/{len(items)}")
        if not items:
            return 0, []
        self.paths.ensure_directories()
        records: list[TrashRecord] = []
        errors: list[str] = []
        moved = 0
        for index, item in enumerate(items, start=1):
            source = Path(item.path)
            pending: TrashRecord | None = None
            try:
                if source.is_symlink():
                    raise ValueError("不允许清理符号链接。")
                stat = source.stat()
                # 用户决策：废纸篓是唯一文件来源，不创建任何恢复副本——
                # 清空废纸篓即彻底删除，不残留任何隐藏目录占用空间。
                pending = TrashRecord(
                    original_path=str(source),
                    deleted_at=datetime.now().astimezone().isoformat(),
                    device=stat.st_dev,
                    inode=stat.st_ino,
                )
                # 先落盘恢复记录，再触碰原照片；中断时仍有可追踪记录。
                self._write_undo([*records, pending])
                trash_result = self._send_to_trash(str(source))
                trash_path = Path(trash_result) if trash_result else None
                if trash_path is None and self._trash_locator is not None:
                    trash_path = self._trash_locator(source, stat.st_dev, stat.st_ino)
                if trash_path is not None:
                    pending = replace(pending, trash_path=str(trash_path))
                records.append(pending)
                moved += 1
                self._write_undo(records)
            # 第三方废纸篓库可能包装成任意异常；适配器边界必须保留恢复记录。
            except Exception as exc:  # noqa: BLE001
                error_message = f"{source}：{exc}"
                if source.exists():
                    self._write_undo(records)
                elif pending is not None:
                    # 废纸篓调用可能已移动文件后才报错；保留恢复记录最安全。
                    if self._trash_locator is not None:
                        located = self._trash_locator(source, pending.device, pending.inode)
                        if located is not None:
                            pending = replace(pending, trash_path=str(located))
                    records.append(pending)
                    self._write_undo(records)
                    error_message = (
                        f"{source}：原文件已不在原位置，可能已移入废纸篓；恢复记录已保留。{exc}"
                    )
                errors.append(error_message)
            report_progress(
                progress,
                index,
                len(items),
                f"正在移入废纸篓 {index}/{len(items)} · {source.name}",
            )
        return moved, errors

    def restore(
        self,
        progress: ProgressCallback | None = None,
    ) -> tuple[int, list[str]]:
        if not self.paths.cleanup_undo.exists():
            raise FileNotFoundError("没有可恢复的清理记录。")
        data = json.loads(self.paths.cleanup_undo.read_text(encoding="utf-8"))
        records = data.get("items") or [{"original_path": p} for p in data.get("paths", [])]
        restored = 0
        errors: list[str] = []
        remaining: list[dict[str, object]] = []
        report_progress(progress, 0, len(records), f"正在准备恢复 0/{len(records)}")
        for index, record in enumerate(records, start=1):
            original = Path(record["original_path"])
            if original.exists():
                errors.append(f"原位置已有同名文件，未覆盖：{original.name}")
                remaining.append(record)
                report_progress(
                    progress,
                    index,
                    len(records),
                    f"跳过恢复 {index}/{len(records)} · {original.name}",
                )
                continue
            if not original.parent.is_dir():
                errors.append(f"原文件夹不存在：{original.parent}")
                remaining.append(record)
                report_progress(
                    progress,
                    index,
                    len(records),
                    f"恢复失败 {index}/{len(records)} · {original.name}",
                )
                continue
            done = False
            detail: str | None = None
            # ① 按记录路径或 device/inode 定位废纸篓中的文件（撤回的唯一来源）。
            trash_path = self._locate_trash_item(original, record)
            if trash_path is not None:
                try:
                    shutil.move(str(trash_path), str(original))
                    done = True
                except (OSError, ValueError) as exc:
                    detail = str(exc)
            # ② Finder 放回兑底：处理废纸篓内改名等无法直接定位的情况。
            if not done:
                succeeded, finder_detail = self._restore_fallback(original, record)
                detail = finder_detail or detail
                if succeeded and original.exists():
                    done = True
            if done:
                restored += 1
            else:
                errors.append(
                    f"废纸篓中未找到：{original.name}"
                    + (f"；{detail}" if detail else "；废纸篓可能已被清空，文件已无法找回")
                )
                remaining.append(record)
            report_progress(
                progress,
                index,
                len(records),
                (
                    f"已恢复文件 {index}/{len(records)} · {original.name}"
                    if done
                    else f"恢复失败 {index}/{len(records)} · {original.name}"
                ),
            )
        if remaining:
            data["items"] = remaining
            data["paths"] = [record["original_path"] for record in remaining]
            self._atomic_write(data)
        else:
            self.paths.cleanup_undo.unlink(missing_ok=True)
        return restored, errors

    def has_restore(self) -> bool:
        return self.paths.cleanup_undo.is_file()

    def _locate_trash_item(self, original: Path, record: dict[str, object]) -> Path | None:
        """按记录路径或 device/inode 定位废纸篓中的文件；找不到返回 None。"""
        trash_value = record.get("trash_path")
        trash_path = Path(trash_value) if trash_value else None
        if (trash_path is None or not trash_path.exists()) and self._trash_locator is not None:
            located = self._trash_locator(
                original,
                record.get("device"),
                record.get("inode"),
            )
            if located is not None and located.exists():
                trash_path = located
        if trash_path is not None and trash_path.exists():
            return trash_path
        return None

    def _write_undo(self, records: list[TrashRecord]) -> None:
        if not records:
            self.paths.cleanup_undo.unlink(missing_ok=True)
            return
        payload = {
            "created_at": datetime.now().astimezone().isoformat(),
            "paths": [record.original_path for record in records],
            "items": [asdict(record) for record in records],
        }
        self._atomic_write(payload)

    def _atomic_write(self, payload: dict[str, object]) -> None:
        self.paths.cleanup_undo.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.paths.cleanup_undo.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.paths.cleanup_undo)
