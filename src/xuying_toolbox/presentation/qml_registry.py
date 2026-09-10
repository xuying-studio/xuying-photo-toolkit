"""向 QML 暴露只读应用环境，不放业务逻辑。"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject
from PySide6.QtQml import QQmlApplicationEngine

from xuying_toolbox import __version__
from xuying_toolbox.platform import PlatformInfo
from xuying_toolbox.presentation.application_settings import ApplicationSettingsViewModel
from xuying_toolbox.presentation.viewmodels import (
    CleanupViewModel,
    QuickCutViewModel,
    RenameViewModel,
    XmpSyncViewModel,
)


class ApplicationInfo(QObject):
    def __init__(self, platform_info: PlatformInfo, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._platform_info = platform_info

    @Property(str, constant=True)
    def applicationName(self) -> str:
        return "旭影工具箱"

    @Property(str, constant=True)
    def applicationVersion(self) -> str:
        return __version__

    @Property(str, constant=True)
    def platformName(self) -> str:
        return self._platform_info.system_name

    @Property(str, constant=True)
    def architecture(self) -> str:
        return self._platform_info.architecture

    @Property(str, constant=True)
    def motionPolicy(self) -> str:
        return self._platform_info.motion_policy

    @Property(str, constant=True)
    def effectPolicy(self) -> str:
        return self._platform_info.effect_policy

    @Property(bool, constant=True)
    def platformSupported(self) -> bool:
        return self._platform_info.supported


def register_qml_initial_properties(
    engine: QQmlApplicationEngine,
    application_info: ApplicationInfo,
    application_settings: ApplicationSettingsViewModel,
    rename_view_model: RenameViewModel,
    cleanup_view_model: CleanupViewModel,
    xmp_sync_view_model: XmpSyncViewModel,
    quickcut_view_model: QuickCutViewModel,
) -> None:
    engine.setInitialProperties(
        {
            "applicationName": application_info.applicationName,
            "applicationVersion": application_info.applicationVersion,
            "platformName": application_info.platformName,
            "motionPolicy": application_info.motionPolicy,
            "effectPolicy": application_info.effectPolicy,
            "applicationSettings": application_settings,
            "renameViewModel": rename_view_model,
            "cleanupViewModel": cleanup_view_model,
            "xmpSyncViewModel": xmp_sync_view_model,
            "quickCutViewModel": quickcut_view_model,
        }
    )
