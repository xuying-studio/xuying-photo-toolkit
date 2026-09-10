from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QModelIndex

from xuying_toolbox.domain.models.photo import (
    RenameOperation,
    RenamePlan,
    RenameScanStats,
)
from xuying_toolbox.presentation.models import RenameOperationsModel
from xuying_toolbox.presentation.viewmodels import RenameViewModel


def make_plan(*, conflicts: list[str] | None = None) -> RenamePlan:
    return RenamePlan(
        operations=[
            RenameOperation(
                "/fixtures/IMG0001.ARW",
                "/fixtures/DSC26-09-06-00001.ARW",
                "照片",
            ),
            RenameOperation(
                "/fixtures/IMG0001.JPG",
                "/fixtures/DSC26-09-06-00001.JPG",
                "照片",
            ),
        ],
        image_count=2,
        conflicts=conflicts or [],
        warnings=[],
        stats=RenameScanStats(2, 1, 1, 0, 0, 0),
    )


class FakeRenameUseCase:
    def __init__(
        self,
        plan: RenamePlan | None = None,
        *,
        scan_error: Exception | None = None,
        slow_scan: bool = False,
    ) -> None:
        self.plan = plan or make_plan()
        self.scan_error = scan_error
        self.slow_scan = slow_scan
        self.can_undo = False
        self.scan_thread: int | None = None
        self.scan_recursive: bool | None = None
        self.execute_calls = 0
        self.undo_calls = 0

    def scan(self, _folder, *, recursive=False, progress=None):
        self.scan_thread = threading.get_ident()
        self.scan_recursive = recursive
        if self.scan_error is not None:
            raise self.scan_error
        steps = 80 if self.slow_scan else 2
        for index in range(steps):
            if progress is not None:
                progress(index + 1, steps, f"扫描 {index + 1}/{steps}")
            if self.slow_scan:
                time.sleep(0.004)
        return self.plan

    def execute(self, _plan, progress=None):
        self.execute_calls += 1
        if progress is not None:
            progress(1, 1, "完成")
        self.can_undo = True
        return Path("/fixtures/rename.json")

    def undo(self, progress=None):
        self.undo_calls += 1
        if progress is not None:
            progress(1, 1, "撤回完成")
        self.can_undo = False
        return 2

    def has_undo(self) -> bool:
        return self.can_undo


def test_rename_operations_model_exposes_names_and_paths() -> None:
    model = RenameOperationsModel()
    plan = make_plan()

    model.set_operations(plan.operations)

    assert model.rowCount() == 2
    index = model.index(0, 0, QModelIndex())
    row = model.data(index, model.ModelDataRole)
    assert row == {
        "source": "IMG0001.ARW",
        "target": "DSC26-09-06-00001.ARW",
        "kind": "照片",
        "sourcePath": "/fixtures/IMG0001.ARW",
        "targetPath": "/fixtures/DSC26-09-06-00001.ARW",
    }
    assert model.roleNames()[model.ModelDataRole] == b"modelData"


def test_viewmodel_scans_in_background_and_builds_preview(qtbot, tmp_path: Path) -> None:
    use_case = FakeRenameUseCase()
    view_model = RenameViewModel(use_case)
    main_thread = threading.get_ident()
    view_model.folderPath = str(tmp_path)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as completed:
        view_model.scan()

    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert use_case.scan_thread != main_thread
    assert use_case.scan_recursive is False
    assert completed.args == ["scan", 2]
    assert view_model.phase == "ready"
    assert view_model.operationCount == 2
    assert view_model.stats["rawCount"] == 1
    assert view_model.canExecute
    assert view_model.progressValue == 1.0


def test_viewmodel_requires_confirmation_then_executes_and_undoes(qtbot, tmp_path: Path) -> None:
    use_case = FakeRenameUseCase()
    view_model = RenameViewModel(use_case)
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    with qtbot.waitSignal(view_model.confirmationRequested, timeout=1000) as confirmation:
        view_model.requestExecute()
    assert "2 个照片或 XMP 文件" in confirmation.args[1]
    assert use_case.execute_calls == 0

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as executed:
        view_model.executeConfirmed()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert executed.args == ["execute", 2]
    assert use_case.execute_calls == 1
    assert view_model.canUndo
    assert not view_model.canExecute

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000) as undone:
        view_model.undo()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert undone.args == ["undo", 2]
    assert use_case.undo_calls == 1
    assert not view_model.canUndo
    assert view_model.operationCount == 0


def test_conflict_blocks_execute_and_scan_error_is_structured(qtbot, tmp_path: Path) -> None:
    conflict_case = FakeRenameUseCase(make_plan(conflicts=["目标文件已经存在"]))
    conflict_view_model = RenameViewModel(conflict_case)
    conflict_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(conflict_view_model.actionCompleted, timeout=2000):
        conflict_view_model.scan()
    qtbot.waitUntil(lambda: not conflict_view_model.busy, timeout=2000)

    assert conflict_view_model.phase == "conflict"
    assert conflict_view_model.conflictCount == 1
    assert not conflict_view_model.canExecute
    conflict_view_model.executeConfirmed()
    assert conflict_case.execute_calls == 0

    error_case = FakeRenameUseCase(scan_error=PermissionError("无权读取测试目录"))
    error_view_model = RenameViewModel(error_case)
    error_view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(error_view_model.failed, timeout=2000) as failed:
        error_view_model.scan()
    qtbot.waitUntil(lambda: not error_view_model.busy, timeout=2000)

    assert failed.args == ["permission_denied", "无权读取测试目录"]
    assert error_view_model.phase == "failed"
    assert error_view_model.operationCount == 0
    assert not error_view_model.canExecute


def test_scan_can_cancel_without_leaving_preview(qtbot, tmp_path: Path) -> None:
    use_case = FakeRenameUseCase(slow_scan=True)
    view_model = RenameViewModel(use_case)
    view_model.folderPath = str(tmp_path)

    with qtbot.waitSignal(view_model.progressChanged, timeout=1000):
        view_model.scan()
    assert view_model.busy
    assert view_model.taskCancellable

    with qtbot.waitSignal(view_model.cancelled, timeout=2000):
        view_model.cancel()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert view_model.phase == "cancelled"
    assert view_model.operationCount == 0
    assert "没有修改任何文件" in view_model.statusText


def test_execute_phase_is_explicitly_non_cancellable(qtbot, tmp_path: Path) -> None:
    use_case = FakeRenameUseCase()
    view_model = RenameViewModel(use_case)
    view_model.folderPath = str(tmp_path)
    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=2000):
        view_model.executeConfirmed()
        assert not view_model.taskCancellable
        view_model.cancel()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)

    assert use_case.execute_calls == 1
    assert view_model.phase == "completed"
