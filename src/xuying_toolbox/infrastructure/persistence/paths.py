"""v2 独立数据目录；不会覆盖或写入旧版目录。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


def app_data_dir(app_name: str) -> Path:
    if sys.platform == "win32":
        roaming = os.environ.get("APPDATA")
        base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
        return base / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / app_name


@dataclass(frozen=True, slots=True)
class SupportPaths:
    root: Path
    rename_backups: Path
    cleanup_undo: Path
    xmp_backups: Path
    quickcut_settings: Path
    application_settings: Path
    migration_report: Path

    @classmethod
    def from_root(cls, root: Path) -> SupportPaths:
        return cls(
            root=root,
            rename_backups=root / "rename_backups",
            cleanup_undo=root / "cleanup_undo.json",
            xmp_backups=root / "xmp_backups",
            quickcut_settings=root / "quickcut_settings.json",
            application_settings=root / "application_settings.json",
            migration_report=root / "migration_report.json",
        )

    @classmethod
    def default_v2(cls) -> SupportPaths:
        if override := os.environ.get("XUYING_SUPPORT_ROOT"):
            return cls.from_root(Path(override).expanduser())
        return cls.from_root(app_data_dir("旭影工具箱") / "v2")

    def ensure_directories(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.rename_backups.mkdir(parents=True, exist_ok=True)
        self.xmp_backups.mkdir(parents=True, exist_ok=True)
