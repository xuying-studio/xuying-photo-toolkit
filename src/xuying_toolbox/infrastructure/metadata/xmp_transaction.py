"""XMP 批次备份、原子写入、回滚与撤回。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from xuying_toolbox.domain.models.photo import SyncOperation
from xuying_toolbox.domain.services.progress import ProgressCallback, report_progress
from xuying_toolbox.infrastructure.filesystem.scanner import preferred_sidecar
from xuying_toolbox.infrastructure.metadata.xmp_file import write
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


class LocalXmpTransaction:
    def __init__(self, support: SupportPaths) -> None:
        self.support = support

    def execute(
        self,
        operations: list[SyncOperation],
        progress: ProgressCallback | None = None,
    ) -> tuple[int, Path]:
        if not operations:
            raise ValueError("没有需要同步的项目。")
        self.support.ensure_directories()
        session = self.support.xmp_backups / (
            datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        )
        session.mkdir()
        total_steps = len(operations) * 2
        report_progress(progress, 0, total_steps, f"正在备份目标文件 0/{len(operations)}")
        try:
            manifest = self._prepare_manifest(operations, session, progress, total_steps)
        except Exception:
            # 尚未触碰目标文件，清理未提交的孤立备份会话。
            shutil.rmtree(session, ignore_errors=True)
            raise
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            entries = data["entries"]
            for index, operation in enumerate(operations, start=1):
                target = Path(operation.target)
                write(target, operation.rating, operation.label)
                applied_path = preferred_sidecar(target) if operation.target_is_raw else target
                entries[index - 1]["applied_path"] = str(applied_path)
                entries[index - 1]["applied_sha256"] = self._file_digest(applied_path)
                # 每写完一个目标就落盘指纹，尽量缩小异常中断窗口。
                self._write_json_atomic(manifest, data)
                report_progress(
                    progress,
                    len(operations) + index,
                    total_steps,
                    f"正在写入 XMP 标记 {index}/{len(operations)}",
                )
        except Exception:
            self.restore_manifest(manifest, mark_undone=True, verify_applied=False)
            raise
        return len(operations), manifest

    def _prepare_manifest(
        self,
        operations: list[SyncOperation],
        session: Path,
        progress: ProgressCallback | None,
        total_steps: int,
    ) -> Path:
        entries: list[dict[str, object]] = []
        for index, operation in enumerate(operations):
            target = Path(operation.target)
            entry: dict[str, object] = {
                "target": str(target),
                "target_is_raw": operation.target_is_raw,
            }
            if operation.target_is_raw:
                sidecar = preferred_sidecar(target)
                entry.update(sidecar=str(sidecar), sidecar_existed=sidecar.exists())
                if sidecar.exists():
                    backup_name = f"{index:05d}_{sidecar.name}.bak"
                    shutil.copy2(sidecar, session / backup_name)
                    entry["backup_name"] = backup_name
                    entry["original_sha256"] = self._file_digest(sidecar)
            else:
                backup_name = f"{index:05d}_{target.name}.bak"
                backup = session / backup_name
                try:
                    os.link(target, backup)
                    backup_method = "hardlink"
                except OSError:
                    shutil.copy2(target, backup)
                    backup_method = "copy"
                entry.update(backup_name=backup_name, backup_method=backup_method)
                entry["original_sha256"] = self._file_digest(target)
            entries.append(entry)
            report_progress(
                progress,
                index + 1,
                total_steps,
                f"正在备份目标文件 {index + 1}/{len(operations)} · {target.name}",
            )

        manifest = session / "manifest.json"
        self._write_json_atomic(
            manifest,
            {
                "created_at": datetime.now().astimezone().isoformat(),
                "undone_at": None,
                "entries": entries,
            },
        )
        return manifest

    def restore_manifest(
        self,
        manifest: Path,
        *,
        mark_undone: bool = True,
        progress: ProgressCallback | None = None,
        verify_applied: bool = False,
    ) -> int:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        entries = data.get("entries", [])
        if verify_applied:
            self._verify_undo_targets(entries)
        restored = 0
        report_progress(progress, 0, len(entries), f"正在恢复 XMP 备份 0/{len(entries)}")
        for index, entry in enumerate(entries, start=1):
            if entry.get("restored_at"):
                report_progress(
                    progress,
                    index,
                    len(entries),
                    f"已恢复 XMP 备份 {index}/{len(entries)}",
                )
                continue
            target = Path(entry["target"])
            backup_name = entry.get("backup_name")
            if entry.get("target_is_raw"):
                sidecar = Path(entry["sidecar"])
                if entry.get("sidecar_existed") and backup_name:
                    shutil.copy2(manifest.parent / str(backup_name), sidecar)
                elif not entry.get("sidecar_existed"):
                    sidecar.unlink(missing_ok=True)
            elif backup_name:
                shutil.copy2(manifest.parent / str(backup_name), target)
            restored += 1
            entry["restored_at"] = datetime.now().astimezone().isoformat()
            # 分批落盘恢复进度，失败后重试不会再覆盖已恢复项。
            self._write_json_atomic(manifest, data)
            report_progress(
                progress,
                index,
                len(entries),
                f"正在恢复 XMP 备份 {index}/{len(entries)} · {target.name}",
            )
        if mark_undone:
            data["undone_at"] = datetime.now().astimezone().isoformat()
            self._write_json_atomic(manifest, data)
        return restored

    def undo_latest(self, progress: ProgressCallback | None = None) -> int:
        manifests = (
            sorted(self.support.xmp_backups.glob("*/manifest.json"), reverse=True)
            if self.support.xmp_backups.exists()
            else []
        )
        for manifest in manifests:
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if not data.get("undone_at"):
                return self.restore_manifest(
                    manifest,
                    progress=progress,
                    verify_applied=True,
                )
        raise FileNotFoundError("没有可撤回的同步记录。")

    def has_undo(self) -> bool:
        if not self.support.xmp_backups.exists():
            return False
        for manifest in sorted(self.support.xmp_backups.glob("*/manifest.json"), reverse=True):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if not data.get("undone_at"):
                return True
        return False

    def _verify_undo_targets(self, entries: list[dict[str, object]]) -> None:
        conflicts: list[str] = []
        for entry in entries:
            if entry.get("restored_at") or self._matches_original_state(entry):
                continue
            applied_value = entry.get("applied_path")
            applied_digest = entry.get("applied_sha256")
            if not applied_value or not applied_digest:
                conflicts.append(f"撤回记录缺少执行后指纹：{entry.get('target', '')}")
                continue
            applied_path = Path(str(applied_value))
            if not applied_path.is_file():
                conflicts.append(f"同步后目标已不存在：{applied_path}")
                continue
            if self._file_digest(applied_path) != applied_digest:
                conflicts.append(f"同步后目标又被修改，未覆盖：{applied_path}")
        if conflicts:
            raise FileExistsError("\n".join(conflicts))

    def _matches_original_state(self, entry: dict[str, object]) -> bool:
        if entry.get("target_is_raw"):
            original = Path(str(entry["sidecar"]))
            if not entry.get("sidecar_existed"):
                return not original.exists()
        else:
            original = Path(str(entry["target"]))
        digest = entry.get("original_sha256")
        return bool(digest and original.is_file() and self._file_digest(original) == digest)

    @staticmethod
    def _file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _write_json_atomic(self, path: Path, payload: dict[str, object]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
