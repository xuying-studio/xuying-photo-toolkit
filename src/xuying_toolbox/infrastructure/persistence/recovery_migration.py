"""旧版撤回数据的只读、幂等迁移。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xuying_toolbox.infrastructure.persistence.paths import SupportPaths, app_data_dir


@dataclass(frozen=True, slots=True)
class RecoveryMigrationResult:
    summary: str
    migrated_cleanup_records: int
    manual_rename_records: int
    manual_xmp_records: int


class LegacyRecoveryMigrator:
    def __init__(
        self,
        support: SupportPaths,
        *,
        legacy_root: Path | None = None,
    ) -> None:
        self._support = support
        self._legacy_root = legacy_root or app_data_dir("摄影文件后期处理助手")

    def migrate(self) -> RecoveryMigrationResult:
        existing = self._load_report()
        if existing is not None:
            return existing

        cleanup_records, cleanup_status = self._migrate_cleanup()
        rename_records = len(tuple((self._legacy_root / "rename_backups").glob("*.json")))
        xmp_records = len(tuple((self._legacy_root / "xmp_backups").glob("*/manifest.json")))
        manual_actions = []
        if rename_records:
            manual_actions.append(
                f"{rename_records} 份旧重命名记录缺少文件指纹，请继续使用旧版撤回。"
            )
        if xmp_records:
            manual_actions.append(
                f"{xmp_records} 份旧 XMP 记录缺少执行后指纹，请继续使用旧版撤回。"
            )
        if cleanup_status:
            manual_actions.append(cleanup_status)

        summary_parts = []
        if cleanup_records:
            summary_parts.append(f"已安全迁移 {cleanup_records} 条清理恢复记录")
        if manual_actions:
            summary_parts.append("部分旧撤回记录保留给旧版处理")
        summary = "；".join(summary_parts) + ("。" if summary_parts else "")
        result = RecoveryMigrationResult(
            summary=summary,
            migrated_cleanup_records=cleanup_records,
            manual_rename_records=rename_records,
            manual_xmp_records=xmp_records,
        )
        self._write_report(result, manual_actions)
        return result

    def _migrate_cleanup(self) -> tuple[int, str]:
        source = self._legacy_root / "cleanup_undo.json"
        if self._support.cleanup_undo.exists() or not source.is_file():
            return 0, ""
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            records = payload.get("items") or [
                {"original_path": path} for path in payload.get("paths", [])
            ]
            if not records or not all(self._cleanup_record_is_safe(record) for record in records):
                return 0, "旧清理记录无法确认安全恢复副本，请继续使用旧版恢复。"
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return 0, "旧清理记录损坏，请继续使用旧版恢复。"

        self._support.root.mkdir(parents=True, exist_ok=True)
        temporary = self._support.cleanup_undo.with_suffix(".tmp")
        temporary.write_bytes(source.read_bytes())
        temporary.replace(self._support.cleanup_undo)
        return len(records), ""

    @staticmethod
    def _cleanup_record_is_safe(record: object) -> bool:
        if not isinstance(record, dict):
            return False
        original_value = record.get("original_path")
        recovery_value = record.get("recovery_path")
        if not isinstance(original_value, str) or not isinstance(recovery_value, str):
            return False
        original = Path(original_value)
        recovery = Path(recovery_value)
        return original.is_absolute() and not original.exists() and recovery.is_file()

    def _load_report(self) -> RecoveryMigrationResult | None:
        if not self._support.migration_report.is_file():
            return None
        try:
            payload = json.loads(self._support.migration_report.read_text(encoding="utf-8"))
            return RecoveryMigrationResult(
                summary=str(payload.get("summary", "")),
                migrated_cleanup_records=int(payload.get("migratedCleanupRecords", 0)),
                manual_rename_records=int(payload.get("manualRenameRecords", 0)),
                manual_xmp_records=int(payload.get("manualXmpRecords", 0)),
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _write_report(
        self,
        result: RecoveryMigrationResult,
        manual_actions: list[str],
    ) -> None:
        self._support.root.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "schemaVersion": 2,
            "sourceVersion": "1.4.0",
            "sourceRoot": str(self._legacy_root),
            "migratedAt": datetime.now().astimezone().isoformat(),
            "summary": result.summary,
            "migratedCleanupRecords": result.migrated_cleanup_records,
            "manualRenameRecords": result.manual_rename_records,
            "manualXmpRecords": result.manual_xmp_records,
            "manualActions": manual_actions,
        }
        temporary = self._support.migration_report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._support.migration_report)


__all__ = ["LegacyRecoveryMigrator", "RecoveryMigrationResult"]
