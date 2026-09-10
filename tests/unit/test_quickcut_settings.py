"""关键词快切设置持久化测试。"""

import json
from pathlib import Path

from xuying_toolbox.domain.models.quickcut import (
    AspectRatioPreset,
    ExportMode,
    NormalizedRect,
    ProjectSettings,
)
from xuying_toolbox.infrastructure.persistence.quickcut_settings import (
    JsonQuickCutSettingsStore,
)


def test_settings_round_trip_and_invalid_file_fallback(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    store = JsonQuickCutSettingsStore(path)
    expected = ProjectSettings(
        aspect_ratio=AspectRatioPreset.CLASSIC_PORTRAIT,
        keyword="幸福定格",
        width=1080,
        height=1440,
        frame_rate=29.97,
        frames_per_image=5,
        target_rect=NormalizedRect(0.2, 0.3, 0.4, 0.1),
        export_mode=ExportMode.FRAME_SEQUENCE,
    )

    store.save(expected)
    assert store.load() == expected

    path.write_text("{bad", encoding="utf-8")
    assert store.load() == ProjectSettings()


def test_legacy_settings_have_provenance_and_only_migrate_once(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    expected = ProjectSettings(keyword="誓言", frames_per_image=6)
    calls = 0

    def read_legacy() -> ProjectSettings:
        nonlocal calls
        calls += 1
        return expected

    store = JsonQuickCutSettingsStore(path, legacy_reader=read_legacy)
    assert store.load() == expected
    assert calls == 1
    assert "已从旧版迁移" in store.migration_summary
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 2
    assert payload["migration"]["sourceDomain"] == "com.xuying.keyword-aligner"

    second = JsonQuickCutSettingsStore(path, legacy_reader=read_legacy)
    assert second.load() == expected
    assert calls == 1


def test_legacy_shape_without_schema_remains_compatible(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "aspectRatio": "3:4",
                "width": 1080,
                "height": 1440,
                "frameRate": 30,
                "framesPerImage": 5,
                "keyword": "幸福",
                "targetRect": {"x": 0.3, "y": 0.4, "width": 0.4, "height": 0.1},
                "exportMode": "MP4 视频",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    loaded = JsonQuickCutSettingsStore(path).load()

    assert loaded.aspect_ratio is AspectRatioPreset.CLASSIC_PORTRAIT
    assert loaded.export_mode is ExportMode.MP4
    assert loaded.keyword == "幸福"
