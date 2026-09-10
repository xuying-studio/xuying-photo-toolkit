"""Qt 应用启动、QML 加载和错误收口。"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from xuying_toolbox import __version__
from xuying_toolbox.domain.errors import AppError, ErrorCode
from xuying_toolbox.infrastructure.composition import (
    create_macos_cleanup_use_case,
    create_macos_quickcut_use_case,
    create_rename_use_case,
    create_xmp_sync_use_case,
)
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import QtQuickCutRenderer
from xuying_toolbox.infrastructure.logging_config import LOGGER_NAME, configure_logging
from xuying_toolbox.infrastructure.persistence.application_settings import (
    JsonApplicationSettingsStore,
)
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.infrastructure.persistence.quickcut_settings import (
    JsonQuickCutSettingsStore,
)
from xuying_toolbox.infrastructure.persistence.recovery_migration import LegacyRecoveryMigrator
from xuying_toolbox.platform import PlatformInfo, PlatformKind, detect_platform
from xuying_toolbox.platform.macos.visual_effect import (
    MacMotionMonitor,
    MacVisualEffectAdapter,
)
from xuying_toolbox.presentation.application_settings import ApplicationSettingsViewModel
from xuying_toolbox.presentation.qml_registry import (
    ApplicationInfo,
    register_qml_initial_properties,
)
from xuying_toolbox.presentation.quickcut_preview import QuickCutPreviewProvider
from xuying_toolbox.presentation.viewmodels import (
    CleanupViewModel,
    QuickCutViewModel,
    RenameViewModel,
    XmpSyncViewModel,
)

# 自定义设计系统需要可定制的 Qt Quick Controls 风格，且必须在首次加载 QML 前设置。
QQuickStyle.setStyle("Basic")


@dataclass(slots=True)
class ApplicationRuntime:
    app: QGuiApplication
    engine: QQmlApplicationEngine
    application_info: ApplicationInfo
    platform_info: PlatformInfo
    qml_root: Path
    rename_view_model: RenameViewModel
    cleanup_view_model: CleanupViewModel
    xmp_sync_view_model: XmpSyncViewModel
    quickcut_view_model: QuickCutViewModel
    quickcut_preview_provider: QuickCutPreviewProvider
    application_settings: ApplicationSettingsViewModel
    visual_effect_adapter: MacVisualEffectAdapter | None
    motion_monitor: MacMotionMonitor | None


def resolve_qml_root() -> Path:
    override = os.environ.get("XUYING_QML_DIR")
    if override:
        override_path = Path(override).expanduser().resolve()
        if (override_path / "App.qml").is_file():
            return override_path
        raise AppError(
            ErrorCode.QML_NOT_FOUND,
            "找不到应用界面资源。",
            detail=str(override_path / "App.qml"),
        )

    bundle_root = getattr(sys, "_MEIPASS", None)
    candidates = []
    if bundle_root:
        candidates.append(Path(cast(str, bundle_root)) / "qml")
    candidates.extend(
        [
            Path(__file__).resolve().parents[2] / "qml",
            Path(sys.executable).resolve().parent / "qml",
        ]
    )
    for candidate in candidates:
        if (candidate / "App.qml").is_file():
            return candidate.resolve()
    raise AppError(
        ErrorCode.QML_NOT_FOUND,
        "找不到应用界面资源。",
        detail="已检查开发目录与打包资源目录。",
    )


def create_runtime(argv: Sequence[str] | None = None) -> ApplicationRuntime:
    arguments = list(argv) if argv is not None else list(sys.argv)
    existing = QCoreApplication.instance()
    app = cast(QGuiApplication, existing) if existing is not None else QGuiApplication(arguments)
    app.setApplicationName("旭影工具箱")
    app.setOrganizationName("旭影工作室")
    app.setApplicationVersion(__version__)

    platform_info = detect_platform()
    qml_root = resolve_qml_root()
    app.setWindowIcon(QIcon(str(qml_root / "Assets/app_icon.png")))
    engine = QQmlApplicationEngine()
    quickcut_preview_provider = QuickCutPreviewProvider()
    engine.addImageProvider("quickcut-preview", quickcut_preview_provider)
    application_info = ApplicationInfo(platform_info, engine)
    support_paths = SupportPaths.default_v2()
    recovery_migration = LegacyRecoveryMigrator(support_paths).migrate()
    application_settings = ApplicationSettingsViewModel(
        JsonApplicationSettingsStore(support_paths.application_settings),
        recovery_migration_summary=recovery_migration.summary,
        parent=engine,
    )
    rename_view_model = RenameViewModel(
        create_rename_use_case(support_paths),
        engine,
    )
    cleanup_view_model = CleanupViewModel(
        create_macos_cleanup_use_case(support_paths),
        engine,
        # 阶段 4 先交付 Mac；其他平台可扫描，但不开放移动和恢复。
        platform_ready=platform_info.kind is PlatformKind.MACOS,
    )
    xmp_sync_view_model = XmpSyncViewModel(
        create_xmp_sync_use_case(support_paths),
        engine,
    )
    quickcut_renderer = QtQuickCutRenderer()
    quickcut_view_model = QuickCutViewModel(
        create_macos_quickcut_use_case(quickcut_renderer),
        JsonQuickCutSettingsStore(support_paths.quickcut_settings),
        quickcut_preview_provider,
        quickcut_renderer,
        engine,
    )
    register_qml_initial_properties(
        engine,
        application_info,
        application_settings,
        rename_view_model,
        cleanup_view_model,
        xmp_sync_view_model,
        quickcut_view_model,
    )
    engine.load(QUrl.fromLocalFile(str(qml_root / "App.qml")))
    if not engine.rootObjects():
        raise AppError(
            ErrorCode.QML_LOAD_FAILED,
            "应用界面加载失败。",
            detail=str(qml_root / "App.qml"),
        )
    visual_effect_adapter = None
    motion_monitor = None
    root_window = cast(QWindow, engine.rootObjects()[0])
    if platform_info.kind is PlatformKind.MACOS and app.platformName() == "cocoa":
        # QML 已设为可见，先让 Cocoa 完成 NSWindow 挂接再融合标题栏。
        app.processEvents()
        visual_effect_adapter = MacVisualEffectAdapter()
        if visual_effect_adapter.available and visual_effect_adapter.install(root_window):
            root_window.setProperty(
                "integratedTitleBar",
                visual_effect_adapter.uses_integrated_title_bar(),
            )
            motion_monitor = MacMotionMonitor(visual_effect_adapter, root_window)
            motion_monitor.policyChanged.connect(root_window.setMotionPolicy)
            motion_monitor.start()

            def release_macos_visuals() -> None:
                motion_monitor.stop()
                visual_effect_adapter.destroy()

            app.aboutToQuit.connect(release_macos_visuals)

    # 自动退出只用于 CI 和打包冒烟测试，正常启动不设置该变量。
    auto_quit_ms = int(os.environ.get("XUYING_AUTO_QUIT_MS", "0"))
    if auto_quit_ms > 0:
        QTimer.singleShot(auto_quit_ms, app.quit)
    return ApplicationRuntime(
        app,
        engine,
        application_info,
        platform_info,
        qml_root,
        rename_view_model,
        cleanup_view_model,
        xmp_sync_view_model,
        quickcut_view_model,
        quickcut_preview_provider,
        application_settings,
        visual_effect_adapter,
        motion_monitor,
    )


def run(argv: Sequence[str] | None = None) -> int:
    log_path = configure_logging()
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("启动旭影工具箱 %s，日志：%s", __version__, log_path)
    try:
        runtime = create_runtime(argv)
    except AppError as exc:
        logger.exception("启动失败：%s", exc.to_dict())
        return 2
    logger.info(
        "QML 空壳已加载：platform=%s architecture=%s",
        runtime.platform_info.kind.value,
        runtime.platform_info.architecture,
    )
    return runtime.app.exec()
