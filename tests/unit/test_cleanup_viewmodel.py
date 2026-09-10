from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QModelIndex

from xuying_toolbox.domain.models.photo import CleanupItem, CleanupScanResult
from xuying_toolbox.presentation.models import CleanupItemsModel
from xuying_toolbox.presentation.viewmodels import CleanupViewModel


def make_result() -> CleanupScanResult:
    return CleanupScanResult(
        items=[CleanupItem("/fixtures/A001.JPG", "RAW")],
        total_images=3,
        raw_count=1,
        jpg_count=2,
        target_count=2,
        paired_target_count=1,
    )


class FakeCleanupUseCase:
    def __init__(
        self,
        *,
        scan_error: Exception | None = None,
        slow_scan: bool = False,
        execute_errors: list[str] | None = None,
    ) -> None:
        self.scan_error = scan_error
        self.slow_scan = slow_scan
        self.execute_errors = execute_errors or []
        self.scan_thread: int | None = None
        self.scan_recursive: bool | None = None
        self.execute_calls = 0
        self.restore_calls = 0
        self.restore_available = False

    def scan(self, _folder, _delete_kind, *, recursive=False, progress=None):
        self.scan_thread = threading.get_ident()
        self.scan_recursive = recursive
        if self.scan_error is not None:
            raise self.scan_error
        steps = 80 if self.slow_scan else 2
        for index in range(steps):
            if progress is not None:
                progress(index + 1, steps, f"检查 {index + 1}/{steps}")
            if self.slow_scan:
                time.sleep(0.004)
        return make_result()

    def execute(self, progress=None):
        self.execute_calls += 1
        if progress is not None:
            progress(1, 1, "完成")
        self.restore_available = True
        return 1, list(self.execute_errors)

    def restore(self, progress=None):
        self.restore_calls += 1
        if progress is not None:
            progress(1, 1, "恢复完成")
        self.restore_available = False
        return 1, []

    def has_restore(self) -> bool:
        return self.restore_available


def test_cleanup_items_model_exposes_preview_fields() -> None:
    model = CleanupItemsModel()
    model.set_items(make_result().items)

    assert model.rowCount() == 1
    row = model.data(model.index(0, 0, QModelIndex()), model.ModelDataRole)
    assert row == {
        "name": "A001.JPG",
        "missing": "RAW",
        "action": "移入系统废纸篓",
        "path": "/fixtures/A001.JPG",
    }
    assert model.roleNames()[model.ModelDataRole] == b"modelData"


def test_viewmodel_scans_in_background_and_requires_confirmation(qtbot, tmp_path: Path) -> None:
    use_case = FakeCleanupUseCase()
    view_model = CleanupViewModel(use_case)
    main_thread = threading.get_ident()
    view_model.folderPath = str(tmp_path)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as completed:
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert use_case.scan_thread != main_thread
    assert use_case.scan_recursive is False
    assert completed.args == ["scan", 1]
    assert view_model.phase == "ready"
    assert view_model.itemCount == 1
    assert view_model.stats["pairedTargetCount"] == 1
    assert view_model.canExecute

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000) as confirmation:
        view_model.requestExecute()
    assert "1 个文件" in confirmation.args[1]
    assert use_case.execute_calls == 0


def test_execute_is_non_cancellable_and_enables_restore(qtbot, tmp_path: Path) -> None:
    use_case = FakeCleanupUseCase()
    view_model = CleanupViewModel(use_case)
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as completed:
        view_model.executeConfirmed()
        assert not view_model.taskCancellable
        view_model.cancel()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert completed.args == ["execute", 1]
    assert use_case.execute_calls == 1
    assert view_model.phase == "completed"
    assert view_model.canRestore
    assert not view_model.canExecute

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as restored:
        view_model.restore()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert restored.args == ["restore", 1]
    assert use_case.restore_calls == 1
    assert not view_model.canRestore


def test_partial_execute_surfaces_errors_and_keeps_restore(qtbot, tmp_path: Path) -> None:
    use_case = FakeCleanupUseCase(execute_errors=["一个文件状态不确定"])
    view_model = CleanupViewModel(use_case)
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.executeConfirmed()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert view_model.phase == "partial"
    assert view_model.errorCount == 1
    assert view_model.errors == ["一个文件状态不确定"]
    assert view_model.canRestore


def test_scan_error_and_cancel_leave_no_preview(qtbot, tmp_path: Path) -> None:
    error_case = FakeCleanupUseCase(scan_error=PermissionError("无权读取测试目录"))
    error_view_model = CleanupViewModel(error_case)
    error_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(error_view_model.failed, timeout=2000) as failed:
        error_view_model.scan()
    qtbot.waitUntil(lambda: not error_view_model.busy, timeout=2000)
    assert failed.args == ["permission_denied", "无权读取测试目录"]
    assert error_view_model.itemCount == 0
    assert not error_view_model.canExecute

    slow_case = FakeCleanupUseCase(slow_scan=True)
    cancel_view_model = CleanupViewModel(slow_case)
    cancel_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(cancel_view_model.progressChanged, timeout=1000):
        cancel_view_model.scan()
    with qtbot.waitSignal(cancel_view_model.cancelled, timeout=2000):
        cancel_view_model.cancel()
    qtbot.waitUntil(lambda: not cancel_view_model.busy, timeout=2000)
    assert cancel_view_model.phase == "cancelled"
    assert cancel_view_model.itemCount == 0
    assert "没有移动任何文件" in cancel_view_model.statusText


def test_non_macos_mode_allows_scan_but_blocks_write_actions(
    qtbot,
    tmp_path: Path,
) -> None:
    use_case = FakeCleanupUseCase()
    view_model = CleanupViewModel(use_case, platform_ready=False)
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert view_model.itemCount == 1
    assert not view_model.canExecute
    assert not view_model.canRestore
    view_model.executeConfirmed()
    assert use_case.execute_calls == 0
