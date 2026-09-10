"""关键词快切从 QML 状态到 Apple Vision 的真实工作流测试。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl

from xuying_toolbox.bootstrap import create_runtime
from xuying_toolbox.domain.models.quickcut import DEFAULT_TARGET_RECT
from xuying_toolbox.domain.services.quickcut import alignment_geometry, transformed_box
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


@pytest.mark.qml
@pytest.mark.skipif(sys.platform != "darwin", reason="仅在 macOS 验证 Apple Vision 工作流")
def test_quickcut_import_recognize_preview_and_page_state(
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root_path = Path(__file__).resolve().parents[2]
    qml_root = root_path / "qml"
    fixture = root_path / "experiments/stage0_ocr/fixtures/03_mixed.png"
    support_paths = SupportPaths.from_root(tmp_path / "support")
    monkeypatch.setenv("XUYING_QML_DIR", str(qml_root))
    monkeypatch.setattr(
        SupportPaths,
        "default_v2",
        classmethod(lambda _cls: support_paths),
    )
    runtime = create_runtime(["xuying-quickcut-workflow-test"])
    root = runtime.engine.rootObjects()[0]
    shell = root.findChild(QObject, "mainShell")
    recognize_button = root.findChild(QObject, "recognizeQuickCutButton")
    export_button = root.findChild(QObject, "exportQuickCutButton")
    qtbot.waitUntil(root.isVisible, timeout=3000)

    shell.setProperty("currentPage", 3)
    runtime.quickcut_view_model.addFileUrls([QUrl.fromLocalFile(str(fixture))])
    runtime.quickcut_view_model.setKeyword("Wedding 2026")

    assert runtime.quickcut_view_model.itemCount == 1
    assert recognize_button.property("enabled") is True
    assert export_button.property("enabled") is True
    preview_before = runtime.quickcut_view_model.previewUrl

    with qtbot.waitSignal(runtime.quickcut_view_model.actionCompleted, timeout=10_000) as signal:
        runtime.quickcut_view_model.recognizeAll()
    qtbot.waitUntil(lambda: not runtime.quickcut_view_model.busy, timeout=3000)

    assert signal.args == ["recognize", 1]
    assert runtime.quickcut_view_model.candidateLabels
    assert "精确" in runtime.quickcut_view_model.candidateLabels[0]
    selected_item = runtime.quickcut_view_model._selected_item()
    assert selected_item is not None
    assert selected_item.selected_candidate is not None
    natural_geometry = alignment_geometry(
        selected_item.width,
        selected_item.height,
        runtime.quickcut_view_model.outputWidth,
        runtime.quickcut_view_model.outputHeight,
        None,
        DEFAULT_TARGET_RECT,
    )
    expected_box = transformed_box(
        selected_item.selected_candidate.box,
        selected_item.width,
        selected_item.height,
        runtime.quickcut_view_model.outputWidth,
        runtime.quickcut_view_model.outputHeight,
        natural_geometry,
    ).clamped()
    assert runtime.quickcut_view_model.targetX == pytest.approx(expected_box.x)
    assert runtime.quickcut_view_model.targetY == pytest.approx(expected_box.y)
    assert runtime.quickcut_view_model.targetWidth == pytest.approx(expected_box.width)
    assert runtime.quickcut_view_model.targetHeight == pytest.approx(expected_box.height)

    runtime.quickcut_view_model.updateTargetRect(0.2, 0.3, 0.4, 0.1)
    assert runtime.quickcut_view_model.previewUrl != preview_before
    runtime.quickcut_view_model.resetTargetRect()
    assert runtime.quickcut_view_model.targetX == pytest.approx(expected_box.x)
    assert runtime.quickcut_view_model.targetY == pytest.approx(expected_box.y)
    assert runtime.quickcut_view_model.targetWidth == pytest.approx(expected_box.width)
    assert runtime.quickcut_view_model.targetHeight == pytest.approx(expected_box.height)

    shell.setProperty("currentPage", 0)
    shell.setProperty("currentPage", 3)
    assert runtime.quickcut_view_model.itemCount == 1

    root.close()
    runtime.engine.deleteLater()
