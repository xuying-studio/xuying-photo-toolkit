"""旧版恢复记录迁移测试。"""

import json
from pathlib import Path

from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.infrastructure.persistence.recovery_migration import (
    LegacyRecoveryMigrator,
)


def _write_cleanup_record(legacy_root: Path, recovery: Path, original: Path) -> Path:
    source = legacy_root / "cleanup_undo.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "original_path": str(original),
                        "recovery_path": str(recovery),
                        "recovery_method": "safe-copy",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return source


def test_safe_cleanup_record_is_copied_and_migration_is_idempotent(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    recovery = legacy / "recovery.jpg"
    recovery.write_bytes(b"photo")
    source = _write_cleanup_record(legacy, recovery, tmp_path / "missing.jpg")
    source_bytes = source.read_bytes()
    (legacy / "rename_backups").mkdir()
    (legacy / "rename_backups" / "rename.json").write_text("{}", encoding="utf-8")
    manifest = legacy / "xmp_backups" / "one" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    support = SupportPaths.from_root(tmp_path / "v2")

    first = LegacyRecoveryMigrator(support, legacy_root=legacy).migrate()

    assert first.migrated_cleanup_records == 1
    assert first.manual_rename_records == 1
    assert first.manual_xmp_records == 1
    assert support.cleanup_undo.read_bytes() == source_bytes
    assert source.read_bytes() == source_bytes

    # 首次报告是幂等边界：旧版以后新增记录也不会重复导入。
    (legacy / "rename_backups" / "later.json").write_text("{}", encoding="utf-8")
    second = LegacyRecoveryMigrator(support, legacy_root=legacy).migrate()
    assert second == first
    assert support.cleanup_undo.read_bytes() == source_bytes


def test_unsafe_cleanup_record_stays_in_legacy_location(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    missing_recovery = legacy / "missing-recovery.jpg"
    source = _write_cleanup_record(legacy, missing_recovery, tmp_path / "missing.jpg")
    source_bytes = source.read_bytes()
    support = SupportPaths.from_root(tmp_path / "v2")

    result = LegacyRecoveryMigrator(support, legacy_root=legacy).migrate()

    assert result.migrated_cleanup_records == 0
    assert not support.cleanup_undo.exists()
    assert source.read_bytes() == source_bytes
    report = json.loads(support.migration_report.read_text(encoding="utf-8"))
    assert "无法确认安全恢复副本" in report["manualActions"][0]
