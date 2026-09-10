"""应用外观设置迁移测试。"""

import json
from pathlib import Path

from xuying_toolbox.infrastructure.persistence.application_settings import (
    ApplicationSettings,
    JsonApplicationSettingsStore,
)


def test_legacy_theme_is_migrated_read_only_and_only_once(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy" / "ui_config.json"
    legacy.parent.mkdir()
    legacy.write_text('{"skin":"aurora_spatial","opacity":95}', encoding="utf-8")
    original_bytes = legacy.read_bytes()
    target = tmp_path / "v2" / "application_settings.json"

    store = JsonApplicationSettingsStore(target, legacy_paths=(legacy,))
    assert store.load() == ApplicationSettings(theme_id="aurora_spatial")
    assert legacy.read_bytes() == original_bytes
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 2
    assert payload["migration"]["sourcePath"] == str(legacy)
    assert "已从旧版迁移" in store.migration_summary

    # v2 已存在后只读自己的设置，不再受旧版后续变化影响。
    legacy.write_text('{"skin":"soft_3d"}', encoding="utf-8")
    second = JsonApplicationSettingsStore(target, legacy_paths=(legacy,))
    assert second.load() == ApplicationSettings(theme_id="aurora_spatial")


def test_invalid_legacy_theme_does_not_overwrite_source_or_create_v2(tmp_path: Path) -> None:
    legacy = tmp_path / "ui_config.json"
    legacy.write_text('{"skin":"unknown"}', encoding="utf-8")
    original_bytes = legacy.read_bytes()
    target = tmp_path / "v2" / "application_settings.json"

    store = JsonApplicationSettingsStore(target, legacy_paths=(legacy,))

    assert store.load() == ApplicationSettings()
    assert not target.exists()
    assert legacy.read_bytes() == original_bytes
    assert "未覆盖旧文件" in store.migration_summary


def test_theme_round_trip_keeps_migration_provenance(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text('{"skin":"nebula_navy"}', encoding="utf-8")
    target = tmp_path / "application_settings.json"
    store = JsonApplicationSettingsStore(target, legacy_paths=(legacy,))
    store.load()

    store.save(ApplicationSettings(theme_id="liquid_glass"))

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["themeId"] == "liquid_glass"
    assert payload["migration"]["sourcePath"] == str(legacy)
