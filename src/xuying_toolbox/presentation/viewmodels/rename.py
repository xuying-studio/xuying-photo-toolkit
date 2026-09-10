"""时间重命名的 Qt 状态、后台任务与 QML 交互边界。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from xuying_toolbox.application.rename import RenameUseCase
from xuying_toolbox.domain.models.photo import RenamePlan, RenameScanStats
from xuying_toolbox.presentation.models.rename_operations import RenameOperationsModel
from xuying_toolbox.presentation.task_runner import TaskOperation, TaskRunner
from xuying_toolbox.presentation.viewmodels.folder_selection import (
    local_directory_from_url,
)

EMPTY_STATS = RenameScanStats(0, 0, 0, 0, 0, 0)


class RenameViewModel(QObject):
    stateChanged = Signal()
    progressChanged = Signal(int, int, str)
    confirmationRequested = Signal(str, str)
    notificationRequested = Signal(str, str)
    actionCompleted = Signal(str, int)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(
        self,
        use_case: RenameUseCase,
        parent: QObject | None = None,
        *,
        task_runner: TaskRunner | None = None,
    ) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._runner = task_runner or TaskRunner(self)
        self._operations = RenameOperationsModel(self)
        self._folder_path = ""
        self._phase = "idle"
        self._status_text = "请选择照片文件夹"
        self._progress_current = 0
        self._progress_total = 0
        self._plan: RenamePlan | None = None
        self._stats = EMPTY_STATS
        self._conflicts: list[str] = []
        self._warnings: list[str] = []
        self._error_code = ""
        self._error_message = ""
        self._active_action = ""
        self._executed_count = 0
        self._can_undo = self._read_can_undo()

        self._runner.progress.connect(self._on_progress)
        self._runner.succeeded.connect(self._on_succeeded)
        self._runner.failed.connect(self._on_failed)
        self._runner.cancelled.connect(self._on_cancelled)
        self._runner.finished.connect(self._on_finished)

    @Property(str, notify=stateChanged)
    def folderPath(self) -> str:
        return self._folder_path

    @folderPath.setter
    def folderPath(self, value: str) -> None:
        normalized = str(Path(value).expanduser()) if value else ""
        if normalized == self._folder_path or self.busy:
            return
        self._folder_path = normalized
        self._clear_preview()
        self._phase = "idle"
        self._status_text = "可以开始只读扫描" if normalized else "请选择照片文件夹"
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def phase(self) -> str:
        return self._phase

    @Property(str, notify=stateChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=stateChanged)
    def busy(self) -> bool:
        return self._runner.running

    @Property(bool, notify=stateChanged)
    def taskCancellable(self) -> bool:
        return self._runner.cancellable

    @Property(int, notify=stateChanged)
    def progressCurrent(self) -> int:
        return self._progress_current

    @Property(int, notify=stateChanged)
    def progressTotal(self) -> int:
        return self._progress_total

    @Property(float, notify=stateChanged)
    def progressValue(self) -> float:
        return self._progress_current / self._progress_total if self._progress_total else 0.0

    @Property(QObject, constant=True)
    def operationsModel(self) -> QObject:
        return self._operations

    @Property(int, notify=stateChanged)
    def operationCount(self) -> int:
        return self._operations.rowCount()

    @Property("QVariantMap", notify=stateChanged)
    def stats(self) -> dict[str, int]:
        return {
            "totalImages": self._stats.total_images,
            "rawCount": self._stats.raw_count,
            "jpgCount": self._stats.jpg_count,
            "alreadyNamedCount": self._stats.already_named_count,
            "skippedCount": self._stats.skipped_count,
            "xmpCount": self._stats.xmp_count,
        }

    @Property("QStringList", notify=stateChanged)
    def conflicts(self) -> list[str]:
        return list(self._conflicts)

    @Property("QStringList", notify=stateChanged)
    def warnings(self) -> list[str]:
        return list(self._warnings)

    @Property(int, notify=stateChanged)
    def conflictCount(self) -> int:
        return len(self._conflicts)

    @Property(int, notify=stateChanged)
    def warningCount(self) -> int:
        return len(self._warnings)

    @Property(str, notify=stateChanged)
    def errorCode(self) -> str:
        return self._error_code

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(bool, notify=stateChanged)
    def canScan(self) -> bool:
        return bool(self._folder_path) and not self.busy

    @Property(bool, notify=stateChanged)
    def canExecute(self) -> bool:
        return (
            self._plan is not None
            and bool(self._plan.operations)
            and not self._plan.conflicts
            and not self.busy
        )

    @Property(bool, notify=stateChanged)
    def canUndo(self) -> bool:
        return self._can_undo and not self.busy

    @Slot(QUrl)
    def setFolderUrl(self, folder_url: QUrl) -> None:
        folder, error = local_directory_from_url(folder_url)
        if error:
            self.notificationRequested.emit(error, "warning")
            return
        self.folderPath = folder

    @Slot()
    def scan(self) -> None:
        if not self.canScan:
            return
        folder = self._folder_path
        self._clear_preview()
        self._reset_error()
        self._start(
            "scan",
            lambda progress: self._use_case.scan(
                folder,
                # 前台工具固定只处理当前文件夹。
                recursive=False,
                progress=progress,
            ),
            phase="scanning",
            status="正在只读扫描拍摄时间…",
            cancellable=True,
        )

    @Slot()
    def requestExecute(self) -> None:
        if not self.canExecute or self._plan is None:
            return
        count = len(self._plan.operations)
        self.confirmationRequested.emit(
            "确认执行时间重命名",
            f"将修改 {count} 个照片或 XMP 文件的名称。\n执行前会写入撤回记录，且不会覆盖同名文件。",
        )

    @Slot()
    def executeConfirmed(self) -> None:
        if not self.canExecute or self._plan is None:
            return
        plan = self._plan
        self._executed_count = len(plan.operations)
        self._reset_error()
        self._start(
            "execute",
            lambda progress: self._use_case.execute(plan, progress),
            phase="executing",
            status="正在安全提交重命名，此阶段不可中断…",
            cancellable=False,
        )

    @Slot()
    def undo(self) -> None:
        if not self.canUndo:
            return
        self._reset_error()
        self._start(
            "undo",
            lambda progress: self._use_case.undo(progress),
            phase="undoing",
            status="正在安全撤回重命名，此阶段不可中断…",
            cancellable=False,
        )

    @Slot()
    def cancel(self) -> None:
        if self._runner.cancel():
            self._status_text = "正在取消扫描…"
            self.stateChanged.emit()
        elif self.busy:
            self.notificationRequested.emit("当前正在安全提交，完成前不能中断。", "warning")

    def _start(
        self,
        action: str,
        operation: TaskOperation,
        *,
        phase: str,
        status: str,
        cancellable: bool,
    ) -> None:
        self._active_action = action
        self._phase = phase
        self._status_text = status
        self._progress_current = 0
        self._progress_total = 0
        if not self._runner.start(operation, cancellable=cancellable):
            return
        self.stateChanged.emit()

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, message: str) -> None:
        self._progress_current = current
        self._progress_total = total
        self._status_text = message
        self.progressChanged.emit(current, total, message)
        self.stateChanged.emit()

    @Slot(object)
    def _on_succeeded(self, result: Any) -> None:
        action = self._active_action
        if action == "scan":
            plan = result
            if not isinstance(plan, RenamePlan):
                self._on_failed("TypeError", "扫描返回了无效结果。")
                return
            self._plan = plan
            self._stats = plan.stats
            self._conflicts = list(plan.conflicts)
            self._warnings = list(plan.warnings)
            self._operations.set_operations(plan.operations)
            if plan.conflicts:
                self._phase = "conflict"
                self._status_text = f"发现 {len(plan.conflicts)} 个冲突，已禁止执行"
            elif plan.operations:
                self._phase = "ready"
                self._status_text = f"预览已就绪，待重命名 {len(plan.operations)} 个文件"
            else:
                self._phase = "empty"
                self._status_text = "扫描完成，没有需要重命名的文件"
            self.actionCompleted.emit("scan", len(plan.operations))
        elif action == "execute":
            self._plan = None
            self._phase = "completed"
            self._status_text = f"已安全完成 {self._executed_count} 个文件改名"
            self._can_undo = self._read_can_undo()
            self.actionCompleted.emit("execute", self._executed_count)
            self.notificationRequested.emit("时间重命名已完成，可以撤回。", "success")
        elif action == "undo":
            count = int(result)
            self._clear_preview()
            self._phase = "completed"
            self._status_text = f"已撤回 {count} 个文件改名"
            self._can_undo = self._read_can_undo()
            self.actionCompleted.emit("undo", count)
            self.notificationRequested.emit("最近一次时间重命名已撤回。", "success")
        self.stateChanged.emit()

    @Slot(str, str)
    def _on_failed(self, exception_name: str, message: str) -> None:
        self._error_code = self._error_code_for(exception_name)
        self._error_message = message or "操作失败，请重试。"
        self._phase = "failed"
        self._status_text = self._error_message
        if self._active_action == "scan":
            self._clear_preview()
        elif self._active_action == "execute":
            self._plan = None
        self._can_undo = self._read_can_undo()
        self.failed.emit(self._error_code, self._error_message)
        self.notificationRequested.emit(self._error_message, "error")
        self.stateChanged.emit()

    @Slot()
    def _on_cancelled(self) -> None:
        self._clear_preview()
        self._phase = "cancelled"
        self._status_text = "扫描已取消，没有修改任何文件"
        self.cancelled.emit()
        self.stateChanged.emit()

    @Slot()
    def _on_finished(self) -> None:
        self._active_action = ""
        self.stateChanged.emit()

    def _clear_preview(self) -> None:
        self._plan = None
        self._stats = EMPTY_STATS
        self._conflicts = []
        self._warnings = []
        self._operations.clear()
        self._progress_current = 0
        self._progress_total = 0

    def _reset_error(self) -> None:
        self._error_code = ""
        self._error_message = ""

    def _read_can_undo(self) -> bool:
        try:
            return self._use_case.has_undo()
        except (OSError, ValueError):
            return False

    @staticmethod
    def _error_code_for(exception_name: str) -> str:
        return {
            "FileNotFoundError": "not_found",
            "FileExistsError": "conflict",
            "PermissionError": "permission_denied",
            "ValueError": "invalid_operation",
            "OSError": "io_error",
        }.get(exception_name, "unexpected")


__all__ = ["RenameViewModel"]
