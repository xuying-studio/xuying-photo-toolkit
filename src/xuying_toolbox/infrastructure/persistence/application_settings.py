"""应用外观设置；首次启动时只读迁移旧版皮肤。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xuying_toolbox.infrastructure.persistence.paths import app_data_dir

THEME_IDS = (
    "professional_dark",
    "nebula_navy",
    "liquid_glass",
    "bento_modular",
    "editorial_minimal",
    "aurora_spatial",
    "soft_3d",
)


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    theme_id: str = "professional_dark"


def default_legacy_application_settings_paths() -> tuple[Path, ...]:
    return (
        app_data_dir("旭影工具箱") / "ui_config.json",
        app_data_dir("旭影的摄影工具集-关键词内嵌版") / "ui_config.json",
        app_data_dir("旭影的摄影工具集") / "ui_config.json",
        app_data_dir("摄影文件后期处理助手") / "ui_config.json",
    )


class JsonApplicationSettingsStore:
    def __init__(
        self,
        path: Path,
        *,
        legacy_paths: tuple[Path, ...] | None = None,
    ) -> None:
        self._path = path
        self._legacy_paths = legacy_paths or default_legacy_application_settings_paths()
        self._migration: dict[str, str] | None = None
        self._migration_summary = ""

    @property
    def migration_summary(self) -> str:
        return self._migration_summary

    def load(self) -> ApplicationSettings:
        self._migration_summary = ""
        if self._path.is_file():
            try:
                payload = json.loads(self._path.read_text(encoding="utf-8"))
                self._migration = _decode_migration(payload)
                return _decode_settings(payload)
            except (OSError, AttributeError, ValueError, TypeError, json.JSONDecodeError):
                self._migration_summary = "v2 外观设置损坏，已使用默认皮肤。"
                return ApplicationSettings()

        invalid_sources = 0
        for legacy_path in self._legacy_paths:
            if not legacy_path.is_file():
                continue
            try:
                payload = json.loads(legacy_path.read_text(encoding="utf-8"))
                settings = ApplicationSettings(theme_id=_valid_theme(payload.get("skin")))
            except (OSError, AttributeError, ValueError, TypeError, json.JSONDecodeError):
                invalid_sources += 1
                continue
            self._migration = {
                "sourceVersion": "1.4.0",
                "sourcePath": str(legacy_path),
                "migratedAt": datetime.now().astimezone().isoformat(),
            }
            self.save(settings)
            self._migration_summary = f"已从旧版迁移界面皮肤：{settings.theme_id}。"
            return settings

        if invalid_sources:
            self._migration_summary = "检测到损坏的旧版外观设置，未覆盖旧文件。"
        return ApplicationSettings()

    def save(self, settings: ApplicationSettings) -> None:
        payload: dict[str, Any] = {
            "schemaVersion": 2,
            "themeId": _valid_theme(settings.theme_id),
        }
        if self._migration:
            payload["migration"] = self._migration
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._path)


def _valid_theme(value: object) -> str:
    theme_id = str(value or "professional_dark")
    if theme_id not in THEME_IDS:
        raise ValueError(f"未知皮肤：{theme_id}")
    return theme_id


def _decode_settings(payload: dict[str, Any]) -> ApplicationSettings:
    if int(payload.get("schemaVersion", 2)) != 2:
        raise ValueError("不支持的外观设置版本。")
    return ApplicationSettings(theme_id=_valid_theme(payload.get("themeId")))


def _decode_migration(payload: dict[str, Any]) -> dict[str, str] | None:
    migration = payload.get("migration")
    if not isinstance(migration, dict):
        return None
    return {
        key: str(migration[key])
        for key in ("sourceVersion", "sourcePath", "migratedAt")
        if key in migration
    }


__all__ = [
    "THEME_IDS",
    "ApplicationSettings",
    "JsonApplicationSettingsStore",
]
