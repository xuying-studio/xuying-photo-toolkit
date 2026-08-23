"""打包后的 Windows 程序使用的真实回收站自测。"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from . import core


def run_windows_recycle_self_test(work_dir: Path) -> dict[str, object]:
    """创建临时照片，验证移入回收站后可以由当前程序恢复。"""

    if sys.platform != "win32":
        return {"success": False, "errors": ["仅支持在 Windows 执行。"]}

    work_dir.mkdir(parents=True, exist_ok=True)
    support_dir = work_dir / "应用记录"
    photo = work_dir / f"打包程序回收站测试-{uuid.uuid4().hex}.jpg"
    expected_content = b"packaged windows recycle bin self test"
    photo.write_bytes(expected_content)

    original_paths = (
        core.APP_SUPPORT_DIR,
        core.RENAME_BACKUP_DIR,
        core.XMP_BACKUP_DIR,
        core.CLEANUP_UNDO_FILE,
    )
    core.APP_SUPPORT_DIR = support_dir
    core.RENAME_BACKUP_DIR = support_dir / "rename"
    core.XMP_BACKUP_DIR = support_dir / "xmp"
    core.CLEANUP_UNDO_FILE = support_dir / "cleanup_undo.json"

    errors: list[str] = []
    try:
        moved, move_errors = core.move_cleanup_items_to_trash(
            [core.CleanupItem(str(photo), "RAW")]
        )
        errors.extend(move_errors)
        no_backup = not any(work_dir.rglob(core.RECOVERY_DIR_NAME))
        record = json.loads(
            core.CLEANUP_UNDO_FILE.read_text(encoding="utf-8")
        )["items"][0]

        restored, restore_errors = core.restore_latest_cleanup()
        errors.extend(restore_errors)
        content_ok = photo.exists() and photo.read_bytes() == expected_content
        success = (
            moved == 1
            and restored == 1
            and no_backup
            and record.get("recovery_path") is None
            and content_ok
            and not errors
        )
        return {
            "success": success,
            "moved": moved,
            "restored": restored,
            "no_backup": no_backup,
            "content_ok": content_ok,
            "errors": errors,
        }
    except Exception as exc:
        return {"success": False, "errors": [str(exc)]}
    finally:
        (
            core.APP_SUPPORT_DIR,
            core.RENAME_BACKUP_DIR,
            core.XMP_BACKUP_DIR,
            core.CLEANUP_UNDO_FILE,
        ) = original_paths
