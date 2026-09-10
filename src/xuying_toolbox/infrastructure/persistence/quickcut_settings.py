"""关键词快切 v2 设置存储，并只读兼容旧版 macOS 设置。"""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from xuying_toolbox.domain.models.quickcut import (
    AspectRatioPreset,
    ExportMode,
    NormalizedRect,
    ProjectSettings,
)

_LEGACY_KEY = "KeywordAligner.ProjectSettings.v1"


class JsonQuickCutSettingsStore:
    def __init__(
        self,
        path: Path,
        *,
        legacy_reader: Callable[[], ProjectSettings | None] | None = None,
    ) -> None:
        self._path = path
        self._legacy_reader = legacy_reader or self._read_legacy_macos
        self._migration: dict[str, str] | None = None
        self._migration_summary = ""

    @property
    def migration_summary(self) -> str:
        return self._migration_summary

    def load(self) -> ProjectSettings:
        self._migration_summary = ""
        if self._path.is_file():
            try:
                payload = json.loads(self._path.read_text(encoding="utf-8"))
                self._migration = _decode_migration(payload)
                return _decode_settings(payload)
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                self._migration_summary = "v2 快切设置损坏，已使用默认参数。"
                return ProjectSettings()
        legacy = self._legacy_reader()
        if legacy is not None:
            self._migration = {
                "sourceVersion": "1.4.0",
                "sourceDomain": "com.xuying.keyword-aligner",
                "sourceKey": _LEGACY_KEY,
                "migratedAt": datetime.now().astimezone().isoformat(),
            }
            self.save(legacy)
            self._migration_summary = "已从旧版迁移关键词快切设置。"
            return legacy
        return ProjectSettings()

    def save(self, settings: ProjectSettings) -> None:
        if message := settings.validation_message:
            raise ValueError(message)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        payload = _encode_settings(settings)
        payload["schemaVersion"] = 2
        if self._migration:
            payload["migration"] = self._migration
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._path)

    @staticmethod
    def _read_legacy_macos() -> ProjectSettings | None:
        if sys.platform != "darwin":
            return None
        completed = subprocess.run(
            ["defaults", "export", "com.xuying.keyword-aligner", "-"],
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return None
        try:
            domain = plistlib.loads(completed.stdout)
            raw = domain.get(_LEGACY_KEY)
            if not isinstance(raw, bytes):
                return None
            return _decode_settings(json.loads(raw.decode("utf-8")))
        except (
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
            plistlib.InvalidFileException,
        ):
            return None


def _encode_settings(settings: ProjectSettings) -> dict[str, Any]:
    return {
        "aspectRatio": settings.aspect_ratio.value,
        "width": settings.width,
        "height": settings.height,
        "frameRate": settings.frame_rate,
        "framesPerImage": settings.frames_per_image,
        "keyword": settings.keyword,
        "targetRect": {
            "x": settings.target_rect.x,
            "y": settings.target_rect.y,
            "width": settings.target_rect.width,
            "height": settings.target_rect.height,
        },
        "exportMode": settings.export_mode.value,
    }


def _decode_settings(payload: dict[str, Any]) -> ProjectSettings:
    if int(payload.get("schemaVersion", 2)) != 2:
        raise ValueError("不支持的快切设置版本。")
    target = payload.get("targetRect", {})
    export_value = str(payload.get("exportMode", ExportMode.MP4.value))
    export_aliases = {
        "对齐 PNG": ExportMode.ALIGNED_PNG,
        "PNG 帧序列": ExportMode.FRAME_SEQUENCE,
        "MP4 视频": ExportMode.MP4,
    }
    export_mode = export_aliases.get(export_value)
    if export_mode is None:
        export_mode = ExportMode(export_value)
    settings = ProjectSettings(
        aspect_ratio=AspectRatioPreset(
            payload.get("aspectRatio", AspectRatioPreset.PORTRAIT.value)
        ),
        keyword=str(payload.get("keyword", "")),
        width=int(payload.get("width", 1080)),
        height=int(payload.get("height", 1920)),
        frame_rate=float(payload.get("frameRate", 30)),
        frames_per_image=int(payload.get("framesPerImage", 4)),
        target_rect=NormalizedRect(
            float(target.get("x", 0.33)),
            float(target.get("y", 0.475)),
            float(target.get("width", 0.34)),
            float(target.get("height", 0.05)),
        ).clamped(),
        export_mode=export_mode,
    )
    if message := settings.validation_message:
        raise ValueError(message)
    return settings


def _decode_migration(payload: dict[str, Any]) -> dict[str, str] | None:
    migration = payload.get("migration")
    if not isinstance(migration, dict):
        return None
    return {key: str(value) for key, value in migration.items()}


__all__ = ["JsonQuickCutSettingsStore"]
