from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QModelIndex

from xuying_toolbox.domain.models.photo import SyncOperation, SyncScanResult
from xuying_toolbox.presentation.models import SyncOperationsModel
from xuying_toolbox.presentation.viewmodels import XmpSyncViewModel


def make_result() -> SyncScanResult:
    return SyncScanResult(
        operations=[
            SyncOperation(
                source="/fixtures/A001.JPG",
                target="/fixtures/A001.ARW",
                target_is_raw=True,
                rating=5,
                label="Red",
                old_rating=0,
                old_label=None,
            )
        ],
        total_images=2,
        source_count=1,
        target_count=1,
        matched_count=1,
        marked_count=1,
        up_to_date_count=0,
    )


class FakeXmpUseCase:
    def __init__(
        self,
        *,
        scan_error: Exception | None = None,
        slow_scan: bool = False,
        undo_error: Exception | None = None,
        undo_available: bool = False,
    ) -> None:
        self.scan_error = scan_error
        self.slow_scan = slow_scan
        self.undo_error = undo_error
        self.undo_available = undo_available
        self.scan_thread: int | None = None
        self.scan_recursive: bool | None = None
        self.execute_calls = 0
        self.undo_calls = 0

    def scan(
        self,
        _folder,
        _direction,
        _sync_rating,
        _sync_label,
        *,
        recursive=False,
        progress=None,
    ):
        self.scan_thread = threading.get_ident()
        self.scan_recursive = recursive
        if self.scan_error is not None:
            raise self.scan_error
        steps = 80 if self.slow_scan else 2
        for index in range(steps):
            if progress is not None:
                progress(index + 1, steps, f"读取 {index + 1}/{steps}")
            if self.slow_scan:
                time.sleep(0.004)
        return make_result()

    def execute(self, _operations, progress=None):
        self.execute_calls += 1
        if progress is not None:
            progress(2, 2, "同步完成")
        self.undo_available = True
        return 1, Path("/fixtures/manifest.json")

    def undo(self, progress=None):
        self.undo_calls += 1
        if self.undo_error is not None:
            raise self.undo_error
        if progress is not None:
            progress(1, 1, "撤回完成")
        self.undo_available = False
        return 1

    def has_undo(self) -> bool:
        return self.undo_available


def test_sync_operations_model_describes_changes() -> None:
    model = SyncOperationsModel()
    model.set_operations(make_result().operations)

    assert model.rowCount() == 1
    row = model.data(model.index(0, 0, QModelIndex()), model.ModelDataRole)
    assert row == {
        "source": "A001.JPG",
        "target": "A001.ARW",
        "rating": "无 → 5",
        "label": "无 → Red",
        "sourcePath": "/fixtures/A001.JPG",
        "targetPath": "/fixtures/A001.ARW",
    }


def test_viewmodel_scans_in_background_and_requires_confirmation(qtbot, tmp_path: Path) -> None:
    use_case = FakeXmpUseCase()
    view_model = XmpSyncViewModel(use_case)
    main_thread = threading.get_ident()
    view_model.folderPath = str(tmp_path)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as completed:
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert use_case.scan_thread != main_thread
    assert use_case.scan_recursive is False
    assert completed.args == ["scan", 1]
    assert view_model.phase == "ready"
    assert view_model.operationCount == 1
    assert view_model.stats["matchedCount"] == 1
    assert view_model.canExecute

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000) as confirmation:
        view_model.requestExecute()
    assert "1 个RAW 侧车文件" in confirmation.args[1]
    assert use_case.execute_calls == 0


def test_option_change_invalidates_preview_and_both_fields_off_block_scan(
    qtbot,
    tmp_path: Path,
) -> None:
    view_model = XmpSyncViewModel(FakeXmpUseCase())
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    view_model.direction = "RAW → JPG"
    assert view_model.operationCount == 0
    assert not view_model.canExecute
    view_model.syncRating = False
    view_model.syncLabel = False
    assert not view_model.canScan
    assert "至少选择" in view_model.statusText


def test_execute_and_undo_are_non_cancellable(qtbot, tmp_path: Path) -> None:
    use_case = FakeXmpUseCase()
    view_model = XmpSyncViewModel(use_case)
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
    assert view_model.canUndo
    assert Path(view_model.manifestPath) == Path("/fixtures/manifest.json")

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as undone:
        view_model.undo()
        assert not view_model.taskCancellable
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert undone.args == ["undo", 1]
    assert use_case.undo_calls == 1
    assert not view_model.canUndo


def test_undo_conflict_is_explicit_and_keeps_backup_available(qtbot) -> None:
    use_case = FakeXmpUseCase(
        undo_error=FileExistsError("同步后目标又被修改，未覆盖"),
        undo_available=True,
    )
    view_model = XmpSyncViewModel(use_case)

    with qtbot.waitSignal(view_model.failed, timeout=2000) as failed:
        view_model.undo()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert failed.args[0] == "conflict"
    assert view_model.phase == "conflict"
    assert view_model.canUndo
    assert "未覆盖" in view_model.errorMessage


def test_scan_error_and_cancel_leave_no_preview(qtbot, tmp_path: Path) -> None:
    error_view_model = XmpSyncViewModel(
        FakeXmpUseCase(scan_error=ValueError("XMP 结构无法安全读取"))
    )
    error_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(error_view_model.failed, timeout=2000) as failed:
        error_view_model.scan()
    qtbot.waitUntil(lambda: not error_view_model.busy, timeout=2000)
    assert failed.args[0] == "invalid_xmp"
    assert error_view_model.operationCount == 0

    cancel_view_model = XmpSyncViewModel(FakeXmpUseCase(slow_scan=True))
    cancel_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(cancel_view_model.progressChanged, timeout=1000):
        cancel_view_model.scan()
    with qtbot.waitSignal(cancel_view_model.cancelled, timeout=2000):
        cancel_view_model.cancel()
    qtbot.waitUntil(lambda: not cancel_view_model.busy, timeout=2000)
    assert cancel_view_model.phase == "cancelled"
    assert cancel_view_model.operationCount == 0
    assert "没有写入任何文件" in cancel_view_model.statusText
