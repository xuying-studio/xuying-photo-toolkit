from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest

from xuying_toolbox.bootstrap import create_runtime
from xuying_toolbox.domain.models.quickcut import ProjectSettings
from xuying_toolbox.domain.services.xmp import insert_jpeg_xmp
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.infrastructure.persistence.quickcut_settings import (
    JsonQuickCutSettingsStore,
)

THEME_IDS = (
    "professional_dark",
    "nebula_navy",
    "liquid_glass",
    "bento_modular",
    "editorial_minimal",
    "aurora_spatial",
    "soft_3d",
)
MOTION_POLICIES = ("full", "reduced", "none")


def _relative_luminance(color: QColor) -> float:
    def linearize(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue, _ = color.getRgbF()
    return 0.2126 * linearize(red) + 0.7152 * linearize(green) + 0.0722 * linearize(blue)


def _contrast_ratio(first: QColor, second: QColor) -> float:
    values = (_relative_luminance(first), _relative_luminance(second))
    lighter, darker = sorted(values, reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.qml
def test_qml_shell_loads_all_placeholder_pages(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    support_paths = SupportPaths.default_v2()
    JsonQuickCutSettingsStore(
        support_paths.quickcut_settings,
        legacy_reader=lambda: None,
    ).save(ProjectSettings(keyword="AGI"))
    runtime = create_runtime(["xuying-toolbox-qml-test"])
    root = runtime.engine.rootObjects()[0]
    qtbot.waitUntil(root.isVisible, timeout=3000)

    assert root.objectName() == "appWindow"
    required_objects = (
        "mainShell",
        "topBar",
        "topBarDragArea",
        "sidebar",
        "brandIcon",
        "pageStack",
        "renamePage",
        "cleanupPage",
        "xmpSyncPage",
        "quickCutPage",
        "navigationRepeater",
        "themePicker",
        "renameDirectory",
        "renameDirectoryDropArea",
        "chooseFolderButton",
        "previewTable",
        "cleanupDirectory",
        "cleanupFormatLabel",
        "cleanupDirectoryDropArea",
        "chooseCleanupFolderButton",
        "cleanupPreviewTable",
        "xmpDirectory",
        "xmpDirectoryDropArea",
        "chooseXmpFolderButton",
        "xmpPreviewTable",
        "neutralCanvas",
        "quickCutAlignmentBox",
        "quickCutAlignmentBoxLabel",
        "quickCutAlignmentResizeHandle",
        "previewPlaybackBar",
        "previewPlaybackButton",
        "previewPlaybackProgress",
        "previewPlaybackPosition",
        "quickCutKeywordField",
        "quickCutQueue",
        "renamePageTranslate",
        "cleanupPageTranslate",
        "xmpSyncPageTranslate",
        "quickCutPageTranslate",
        "progressFill",
        "progressScale",
    )
    for object_name in required_objects:
        assert root.findChild(QObject, object_name) is not None
    for removed_name in (
        "statusBar",
        "statusPanel",
        "motionPicker",
        "recursiveButton",
        "recursiveCleanupButton",
        "recursiveXmpButton",
    ):
        assert root.findChild(QObject, removed_name) is None

    shell = root.findChild(QObject, "mainShell")
    top_bar = root.findChild(QObject, "topBar")
    page_stack = root.findChild(QObject, "pageStack")
    navigation_repeater = root.findChild(QObject, "navigationRepeater")
    assert navigation_repeater.property("count") == 4
    assert shell.property("thirdToolLabel") == "03  颜色星标同步"
    assert root.findChild(QObject, "cleanupFormatLabel").property("text") == "选择要清除的格式"
    assert root.findChild(QObject, "cleanupKindJpgButton").property("text") == "JPG"
    assert root.findChild(QObject, "cleanupKindRawButton").property("text") == "RAW"
    keyword_field = root.findChild(QObject, "quickCutKeywordField")
    alignment_box_label = root.findChild(QObject, "quickCutAlignmentBoxLabel")
    assert keyword_field.property("text") == ""
    assert keyword_field.property("placeholderText") == "输入要识别的关键词"
    assert alignment_box_label.property("text") == "关键词对齐框"
    assert "关键词目标框" not in (
        qml_root / "Pages" / "QuickCutPage.qml"
    ).read_text(encoding="utf-8")
    for page_name, removed_copy in (
        ("RenamePage.qml", "文件安全规则"),
        ("CleanupPage.qml", "安全边界"),
        ("XmpSyncPage.qml", "写入保护"),
    ):
        assert removed_copy not in (qml_root / "Pages" / page_name).read_text(encoding="utf-8")
    assert runtime.app.windowIcon().isNull() is False
    root.setProperty("integratedTitleBar", True)
    qtbot.waitUntil(lambda: top_bar.property("height") > 66, timeout=1000)
    assert top_bar.property("height") > 66
    assert shell.setProperty("currentPage", 3)
    qtbot.waitUntil(lambda: page_stack.property("currentIndex") == 3, timeout=1000)

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_all_themes_and_motion_policies_fit_minimum_window(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-qml-theme-test"])
    root = runtime.engine.rootObjects()[0]
    root.setWidth(1300)
    root.setHeight(760)
    qtbot.waitUntil(root.isVisible, timeout=3000)
    shell = root.findChild(QObject, "mainShell")
    page_stack = root.findChild(QObject, "pageStack")
    pages = tuple(
        root.findChild(QObject, name)
        for name in ("renamePage", "cleanupPage", "xmpSyncPage", "quickCutPage")
    )

    assert tuple(root.property("availableThemeIds").toVariant()) == THEME_IDS
    assert QColor(root.property("currentCanvasColor")).name() == "#15171b"

    for theme_id in THEME_IDS:
        root.setTheme(theme_id)
        qtbot.waitUntil(
            lambda expected=theme_id: root.property("currentThemeId") == expected,
            timeout=1000,
        )
        text_color = QColor(root.property("currentTextColor"))
        panel_color = QColor(root.property("currentPanelColor"))
        assert _contrast_ratio(text_color, panel_color) >= 4.5

        for policy in MOTION_POLICIES:
            root.setMotionPolicy(policy)
            qtbot.waitUntil(
                lambda expected=policy: root.property("currentMotionPolicy") == expected,
                timeout=1000,
            )
            for page_index, page in enumerate(pages):
                assert shell.setProperty("currentPage", page_index)
                qtbot.waitUntil(
                    lambda expected=page_index: page_stack.property("currentIndex") == expected,
                    timeout=1000,
                )
                assert root.layoutFits()
                assert page.property("width") <= page_stack.property("width")
                assert page.property("height") <= page_stack.property("height")

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_motion_durations_and_keyboard_navigation(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-qml-input-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    page_stack = root.findChild(QObject, "pageStack")
    directory_field = root.findChild(QObject, "renameDirectory")
    choose_folder_button = root.findChild(QObject, "chooseFolderButton")
    scan_rename_button = root.findChild(QObject, "scanRenameButton")
    qtbot.waitUntil(root.isVisible, timeout=3000)

    assert directory_field.property("dropEnabled") is True
    assert directory_field.property("placeholderText") == "选择或拖入照片文件夹"
    assert choose_folder_button.property("enabled") is True
    assert scan_rename_button.property("enabled") is False
    root.setMotionPolicy("full")
    duration_properties = ("motionFast", "motionNormal", "motionSlow")
    full_durations = tuple(root.property(name) for name in duration_properties)
    root.setMotionPolicy("reduced")
    reduced_durations = tuple(
        root.property(name) for name in ("motionFast", "motionNormal", "motionSlow")
    )
    root.setMotionPolicy("none")
    none_durations = tuple(root.property(name) for name in duration_properties)

    duration_pairs = zip(reduced_durations, full_durations, strict=True)
    assert all(reduced < full for reduced, full in duration_pairs)
    assert none_durations == (0, 0, 0)

    root.setMotionPolicy("full")
    rename_page = root.findChild(QObject, "renamePage")
    quickcut_page = root.findChild(QObject, "quickCutPage")
    rename_translate = root.findChild(QObject, "renamePageTranslate")
    quickcut_translate = root.findChild(QObject, "quickCutPageTranslate")

    # 快捷键是高频路径，页面与导航状态必须立即完成。
    qtbot.keyClick(root, Qt.Key.Key_4, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(lambda: page_stack.property("currentIndex") == 3, timeout=1000)
    assert quickcut_page.property("opacity") == 1.0
    assert rename_page.property("opacity") == 0.0
    assert quickcut_translate.property("x") == 0.0

    # 鼠标路径保留短促的空间连续性，不再动画被锚点接管的 Item.x。
    shell.selectPage(0)
    qtbot.wait(30)
    assert -16.0 < rename_translate.property("x") < 0.0
    assert 0.0 < rename_page.property("opacity") < 1.0
    qtbot.waitUntil(lambda: rename_translate.property("x") == 0.0, timeout=500)
    qtbot.waitUntil(lambda: rename_page.property("opacity") == 1.0, timeout=500)

    root.setTheme("editorial_minimal")
    assert page_stack.property("currentIndex") == 0

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_button_and_toast_motion_contracts(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-motion-contract-test"])
    root = runtime.engine.rootObjects()[0]
    button = root.findChild(QObject, "chooseFolderButton")
    toast = root.findChild(QObject, "renameToast")
    qtbot.waitUntil(root.isVisible, timeout=3000)

    root.setMotionPolicy("full")
    scene_point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
    button_point = QPoint(round(scene_point.x()), round(scene_point.y()))
    QTest.mouseMove(root, button_point)
    qtbot.wait(200)
    assert button.property("scale") == 1.0

    QTest.mousePress(
        root,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        button_point,
    )
    qtbot.wait(50)
    assert 0.97 <= button.property("scale") < 1.0
    qtbot.waitUntil(lambda: button.property("scale") == 0.97, timeout=300)
    QTest.mouseRelease(
        root,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(5, 5),
    )
    qtbot.waitUntil(lambda: button.property("scale") == 1.0, timeout=300)

    # 键盘仍能执行按钮功能，但不触发缩放动画。
    shell = root.findChild(QObject, "mainShell")
    raw_button = root.findChild(QObject, "cleanupKindRawButton")
    shell.selectPageImmediately(1)
    raw_button.forceActiveFocus()
    qtbot.keyPress(root, Qt.Key.Key_Space)
    assert raw_button.property("scale") == 1.0
    qtbot.keyRelease(root, Qt.Key.Key_Space)
    qtbot.waitUntil(lambda: runtime.cleanup_view_model.deleteKind == "RAW", timeout=500)
    assert raw_button.property("scale") == 1.0

    shell.selectPageImmediately(0)
    assert toast.property("displayDuration") == 3200
    toast.setProperty("displayDuration", 200)
    for policy in MOTION_POLICIES:
        root.setMotionPolicy(policy)
        toast.show("动效策略测试", "info")
        qtbot.wait(100)
        assert toast.property("message") == "动效策略测试"
        if policy == "reduced":
            assert abs(toast.property("motionOffset")) < 0.01
        if policy != "none":
            qtbot.waitUntil(lambda: toast.property("exiting"), timeout=400)
            assert toast.property("visible") is True
            assert toast.property("message") == "动效策略测试"
        qtbot.waitUntil(lambda: not toast.property("visible"), timeout=600)

    progress_source = (qml_root / "Components" / "XyProgressBar.qml").read_text(
        encoding="utf-8"
    )
    assert "Behavior on width" not in progress_source
    assert "xScale: root.visualPosition" in progress_source

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_product_polish_keeps_action_hierarchy_consistent(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-product-polish-test"])
    root = runtime.engine.rootObjects()[0]
    qtbot.waitUntil(root.isVisible, timeout=3000)

    choose_button = root.findChild(QObject, "chooseFolderButton")
    scan_button = root.findChild(QObject, "scanRenameButton")
    execute_button = root.findChild(QObject, "executeRenameButton")
    undo_button = root.findChild(QObject, "undoRenameButton")
    cleanup_button = root.findChild(QObject, "executeCleanupButton")
    import_button = root.findChild(QObject, "importQuickCutFilesButton")
    confirm_button = root.findChild(QObject, "confirmButton")
    cancel_button = root.findChild(QObject, "cancelButton")
    preview_table = root.findChild(QObject, "previewTable")
    rename_progress = root.findChild(QObject, "renameProgress")

    # 首屏只强调当前最合理的下一步，危险和次要操作保持独立语义。
    assert choose_button.property("prominent") is True
    assert scan_button.property("prominent") is False
    assert execute_button.property("prominent") is True
    assert undo_button.property("quiet") is True
    assert cleanup_button.property("prominent") is True
    assert cleanup_button.property("destructive") is True
    assert import_button.property("prominent") is True
    assert confirm_button.property("prominent") is True
    assert cancel_button.property("quiet") is True
    assert "不会立即修改文件" in preview_table.property("emptyHint")
    assert rename_progress.property("trackVisible") is False
    assert rename_progress.property("opacity") == 0.0

    combo_source = (qml_root / "Components" / "XyComboBox.qml").read_text(
        encoding="utf-8"
    )
    dialog_source = (qml_root / "Dialogs" / "ConfirmDialog.qml").read_text(
        encoding="utf-8"
    )
    app_source = (qml_root / "App.qml").read_text(encoding="utf-8")
    assert "enter: Transition" in combo_source
    assert "exit: Transition" in combo_source
    assert "Overlay.modal" in dialog_source
    assert "Behavior on color" not in app_source

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_work_directory_accepts_folder_drop_and_rejects_file(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-folder-drop-test"])
    root = runtime.engine.rootObjects()[0]
    qtbot.waitUntil(root.isVisible, timeout=3000)

    targets = (
        ("renameDirectory", runtime.rename_view_model),
        ("cleanupDirectory", runtime.cleanup_view_model),
        ("xmpDirectory", runtime.xmp_sync_view_model),
    )
    folder_url = QUrl.fromLocalFile(str(tmp_path))
    for object_name, view_model in targets:
        drop_field = root.findChild(QObject, object_name)
        assert QMetaObject.invokeMethod(
            drop_field,
            "folderDropped",
            Qt.ConnectionType.DirectConnection,
            Q_ARG(QUrl, folder_url),
        )
        assert view_model.folderPath == str(tmp_path)

    file_path = tmp_path / "single-file.jpg"
    file_path.write_bytes(b"fixture")
    rename_drop_field = root.findChild(QObject, "renameDirectory")
    with qtbot.waitSignal(runtime.rename_view_model.notificationRequested, timeout=1000) as notice:
        assert QMetaObject.invokeMethod(
            rename_drop_field,
            "folderDropped",
            Qt.ConnectionType.DirectConnection,
            Q_ARG(QUrl, QUrl.fromLocalFile(str(file_path))),
        )
    assert notice.args == ["请拖入文件夹，不要拖入单个文件。", "warning"]
    assert runtime.rename_view_model.folderPath == str(tmp_path)

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_mac_page_transition_keeps_routing_clickable(qtbot, monkeypatch) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    runtime = create_runtime(["xuying-toolbox-stage6-motion-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    rename_page = root.findChild(QObject, "renamePage")
    quickcut_page = root.findChild(QObject, "quickCutPage")
    qtbot.waitUntil(root.isVisible, timeout=3000)

    root.setMotionPolicy("full")
    shell.setProperty("currentPage", 3)
    assert rename_page.property("enabled") is False
    assert quickcut_page.property("enabled") is True
    qtbot.waitUntil(lambda: quickcut_page.property("opacity") > 0.99, timeout=1000)
    qtbot.waitUntil(lambda: rename_page.property("opacity") < 0.01, timeout=1000)

    # 快切预览层存在时，路由仍不能被覆盖层阻断。
    shell.selectPage(0)
    qtbot.waitUntil(lambda: shell.property("currentPage") == 0, timeout=1000)

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_quickcut_queue_scroll_and_reorder_with_full_motion(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    fixture = Path(__file__).resolve().parents[2] / "experiments/stage0_ocr/fixtures/03_mixed.png"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    paths = []
    fixture_bytes = fixture.read_bytes()
    for index in range(24):
        path = tmp_path / f"queue-{index:02d}.png"
        path.write_bytes(fixture_bytes)
        paths.append(path)

    runtime = create_runtime(["xuying-toolbox-stage6-queue-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    queue = root.findChild(QObject, "quickCutQueue")
    view_model = runtime.quickcut_view_model
    model = view_model.itemsModel
    qtbot.waitUntil(root.isVisible, timeout=3000)

    root.setMotionPolicy("full")
    shell.setProperty("currentPage", 3)
    view_model.addFileUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    qtbot.waitUntil(lambda: view_model.itemCount == len(paths), timeout=2000)
    qtbot.waitUntil(
        lambda: queue.property("contentHeight") > queue.property("height"),
        timeout=2000,
    )

    # 队列获得焦点后，上下键只切换预览图片，不重排队列。
    first_path_before_keyboard = model.data(model.index(0, 0), model.PathRole)
    queue.activateIndex(10)
    assert queue.property("activeFocus") is True
    qtbot.keyClick(root, Qt.Key.Key_Up)
    qtbot.waitUntil(lambda: view_model.selectedIndex == 9, timeout=1000)
    qtbot.keyClick(root, Qt.Key.Key_Down)
    qtbot.waitUntil(lambda: view_model.selectedIndex == 10, timeout=1000)
    assert model.data(model.index(0, 0), model.PathRole) == first_path_before_keyboard
    queue.activateIndex(0)
    qtbot.keyClick(root, Qt.Key.Key_Up)
    assert view_model.selectedIndex == 0
    queue.activateIndex(len(paths) - 1)
    qtbot.keyClick(root, Qt.Key.Key_Down)
    assert view_model.selectedIndex == len(paths) - 1

    # 滚动到队列末端后重排，动效不能重置滚动位置或触发整个模型重建。
    maximum_scroll = queue.property("contentHeight") - queue.property("height")
    queue.setProperty("contentY", maximum_scroll)
    qtbot.waitUntil(lambda: queue.property("contentY") > 0, timeout=1000)
    first_path = model.data(model.index(0, 0), model.PathRole)
    with qtbot.waitSignal(model.rowsMoved, timeout=1000):
        view_model.moveIndex(0, 1)

    assert model.data(model.index(1, 0), model.PathRole) == first_path
    assert queue.property("contentY") > 0

    # 前一次转场未结束时立即反向移动，模型与视图仍要收敛到正确顺序。
    with qtbot.waitSignal(model.rowsMoved, timeout=1000):
        view_model.moveIndex(1, -1)
    assert model.data(model.index(0, 0), model.PathRole) == first_path

    quickcut_source = (qml_root / "Pages" / "QuickCutPage.qml").read_text(
        encoding="utf-8"
    )
    assert 'properties: "x,y"' not in quickcut_source
    assert 'property: "y"' in quickcut_source

    # 画布播放按导出帧率和每图帧数推进，不改变队列顺序。
    playback_button = root.findChild(QObject, "previewPlaybackButton")
    queue.activateIndex(0)
    view_model.setFrameRate("5")
    view_model.setFramesPerImage("1")
    ordered_paths = tuple(
        model.data(model.index(index, 0), model.PathRole)
        for index in range(model.rowCount())
    )
    playback_button.click()
    assert playback_button.property("text") == "暂停"
    qtbot.waitUntil(lambda: view_model.selectedIndex >= 1, timeout=1500)
    playback_button.click()
    assert playback_button.property("text") == "播放"
    assert tuple(
        model.data(model.index(index, 0), model.PathRole)
        for index in range(model.rowCount())
    ) == ordered_paths

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_rename_page_scans_preview_and_opens_confirmation(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    (tmp_path / "IMG0001.ARW").write_bytes(b"raw-fixture")
    (tmp_path / "IMG0001.JPG").write_bytes(b"jpg-fixture")
    runtime = create_runtime(["xuying-toolbox-qml-rename-test"])
    root = runtime.engine.rootObjects()[0]
    view_model = runtime.rename_view_model
    scan_button = root.findChild(QObject, "scanRenameButton")
    execute_button = root.findChild(QObject, "executeRenameButton")
    preview_table = root.findChild(QObject, "previewTable")
    confirm_dialog = root.findChild(QObject, "renameConfirmDialog")
    qtbot.waitUntil(root.isVisible, timeout=3000)

    view_model.folderPath = str(tmp_path)
    qtbot.waitUntil(lambda: scan_button.property("enabled"), timeout=1000)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000) as completed:
        scan_button.click()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert completed.args == ["scan", 2]
    assert preview_table.property("rowCount") == 2
    assert execute_button.property("enabled") is True

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000):
        execute_button.click()
    qtbot.waitUntil(lambda: confirm_dialog.property("visible"), timeout=1000)
    confirm_dialog.close()

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_cleanup_page_scans_preview_and_opens_confirmation(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    (tmp_path / "A001.JPG").write_bytes(b"jpg-fixture")
    runtime = create_runtime(["xuying-toolbox-qml-cleanup-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    view_model = runtime.cleanup_view_model
    scan_button = root.findChild(QObject, "scanCleanupButton")
    execute_button = root.findChild(QObject, "executeCleanupButton")
    preview_table = root.findChild(QObject, "cleanupPreviewTable")
    confirm_dialog = root.findChild(QObject, "cleanupConfirmDialog")
    qtbot.waitUntil(root.isVisible, timeout=3000)
    shell.setProperty("currentPage", 1)

    view_model.folderPath = str(tmp_path)
    qtbot.waitUntil(lambda: scan_button.property("enabled"), timeout=1000)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000) as completed:
        scan_button.click()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert completed.args == ["scan", 1]
    assert preview_table.property("rowCount") == 1
    assert execute_button.property("enabled") is True

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000):
        execute_button.click()
    qtbot.waitUntil(lambda: confirm_dialog.property("visible"), timeout=1000)
    confirm_dialog.close()
    assert (tmp_path / "A001.JPG").read_bytes() == b"jpg-fixture"

    root.close()
    runtime.engine.deleteLater()


@pytest.mark.qml
def test_xmp_page_scans_preview_and_opens_confirmation(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    qml_root = Path(__file__).resolve().parents[2] / "qml"
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    (tmp_path / "A001.JPG").write_bytes(insert_jpeg_xmp(b"\xff\xd8\xff\xd9", 5, "Select"))
    (tmp_path / "A001.ARW").write_bytes(b"raw-fixture")
    runtime = create_runtime(["xuying-toolbox-qml-xmp-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    view_model = runtime.xmp_sync_view_model
    scan_button = root.findChild(QObject, "scanXmpButton")
    execute_button = root.findChild(QObject, "executeXmpButton")
    preview_table = root.findChild(QObject, "xmpPreviewTable")
    confirm_dialog = root.findChild(QObject, "xmpConfirmDialog")
    qtbot.waitUntil(root.isVisible, timeout=3000)
    shell.setProperty("currentPage", 2)

    view_model.folderPath = str(tmp_path)
    qtbot.waitUntil(lambda: scan_button.property("enabled"), timeout=1000)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000) as completed:
        scan_button.click()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert completed.args == ["scan", 1]
    assert preview_table.property("rowCount") == 1
    assert execute_button.property("enabled") is True

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000):
        execute_button.click()
    qtbot.waitUntil(lambda: confirm_dialog.property("visible"), timeout=1000)
    confirm_dialog.close()
    assert not (tmp_path / "A001.xmp").exists()

    root.close()
    runtime.engine.deleteLater()
