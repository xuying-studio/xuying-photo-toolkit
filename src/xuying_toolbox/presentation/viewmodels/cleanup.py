"""RAW/JPG 配对清理的 Qt 状态和安全交互边界。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.domain.models.photo import CleanupScanResult
from xuying_toolbox.presentation.models import CleanupItemsModel
from xuying_toolbox.presentation.task_runner import TaskOperation, TaskRunner
from xuying_toolbox.presentation.viewmodels.folder_selection import (
    local_directory_from_url,
)


class CleanupViewModel(QObject):
    stateChanged = Signal()
    progressChanged = Signal(int, int, str)
    confirmationRequested = Signal(str, str)
    notificationRequested = Signal(str, str)
    actionCompleted = Signal(str, int)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(
        self,
        use_case: CleanupUseCase,
        parent: QObject | None = None,
        *,
        task_runner: TaskRunner | None = None,
        platform_ready: bool = True,
    ) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._runner = task_runner or TaskRunner(self)
        self._items = CleanupItemsModel(self)
        self._platform_ready = platform_ready
        self._folder_path = ""
        self._delete_kind = "JPG"
        self._phase = "idle"
        self._status_text = "请选择照片文件夹"
        self._progress_current = 0
        self._progress_total = 0
        self._result: CleanupScanResult | None = None
        self._errors: list[str] = []
        self._error_code = ""
        self._error_message = ""
        self._active_action = ""
        self._can_restore = self._read_can_restore()

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
        self._status_text = "可以开始只读配对扫描" if normalized else "请选择照片文件夹"
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def deleteKind(self) -> str:
        return self._delete_kind

    @deleteKind.setter
    def deleteKind(self, value: str) -> None:
        normalized = value.upper()
        if normalized not in {"JPG", "RAW"} or normalized == self._delete_kind or self.busy:
            return
        self._delete_kind = normalized
        self._invalidate_preview(f"已改为清理孤立 {normalized}，请重新扫描")

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

    @Property(float, notify=stateChanged)
    def progressValue(self) -> float:
        return self._progress_current / self._progress_total if self._progress_total else 0.0

    @Property(QObject, constant=True)
    def itemsModel(self) -> QObject:
        return self._items

    @Property(int, notify=stateChanged)
    def itemCount(self) -> int:
        return self._items.rowCount()

    @Property("QVariantMap", notify=stateChanged)
    def stats(self) -> dict[str, int]:
        result = self._result
        return {
            "totalImages": result.total_images if result else 0,
            "rawCount": result.raw_count if result else 0,
            "jpgCount": result.jpg_count if result else 0,
            "targetCount": result.target_count if result else 0,
            "pairedTargetCount": result.paired_target_count if result else 0,
        }

    @Property("QStringList", notify=stateChanged)
    def errors(self) -> list[str]:
        return list(self._errors)

    @Property(int, notify=stateChanged)
    def errorCount(self) -> int:
        return len(self._errors)

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
            self._platform_ready
            and self._result is not None
            and bool(self._result.items)
            and not self.busy
        )

    @Property(bool, notify=stateChanged)
    def canRestore(self) -> bool:
        return self._platform_ready and self._can_restore and not self.busy

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
        delete_kind = self._delete_kind
        self._clear_preview()
        self._reset_error()
        self._start(
            "scan",
            lambda progress: self._use_case.scan(
                folder,
                delete_kind,
                # 前台工具固定只处理当前文件夹。
                recursive=False,
                progress=progress,
            ),
            phase="scanning",
            status="正在只读检查 RAW/JPG 配对…",
            cancellable=True,
        )

    @Slot()
    def requestExecute(self) -> None:
        if not self.canExecute or self._result is None:
            return
        self.confirmationRequested.emit(
            f"确认清理孤立 {self._delete_kind}",
            f"将把 {len(self._result.items)} 个文件移入系统废纸篓。\n"
            "每个文件都会先保留安全恢复副本和恢复记录。",
        )

    @Slot()
    def executeConfirmed(self) -> None:
        if not self.canExecute:
            return
        self._reset_error()
        self._start(
            "execute",
            lambda progress: self._use_case.execute(progress),
            phase="executing",
            status="正在创建恢复副本并移入废纸篓，此阶段不可中断…",
            cancellable=False,
        )

    @Slot()
    def restore(self) -> None:
        if not self.canRestore:
            return
        self._reset_error()
        self._start(
            "restore",
            lambda progress: self._use_case.restore(progress),
            phase="restoring",
            status="正在安全恢复最近一次清理，此阶段不可中断…",
            cancellable=False,
        )

    @Slot()
    def cancel(self) -> None:
        if self._runner.cancel():
            self._status_text = "正在取消配对扫描…"
            self.stateChanged.emit()
        elif self.busy:
            self.notificationRequested.emit("当前正在写入恢复记录，完成前不能中断。", "warning")

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
        if self._runner.start(operation, cancellable=cancellable):
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
            if not isinstance(result, CleanupScanResult):
                self._on_failed("TypeError", "扫描返回了无效结果。")
                return
            self._result = result
            self._items.set_items(result.items)
            self._errors = []
            self._phase = "ready" if result.items else "empty"
            self._status_text = (
                f"预览已就绪，发现 {len(result.items)} 个孤立 {self._delete_kind}"
                if result.items
                else f"配对检查完成，没有孤立 {self._delete_kind}"
            )
            self.actionCompleted.emit("scan", len(result.items))
        elif action in {"execute", "restore"}:
            count, errors = result
            self._errors = list(errors)
            self._clear_preview(keep_errors=True)
            self._phase = "partial" if errors else "completed"
            verb = "移入废纸篓" if action == "execute" else "恢复"
            self._status_text = f"已{verb} {count} 个文件"
            if errors:
                self._status_text += f"，{len(errors)} 个项目需要处理"
            self._can_restore = self._read_can_restore()
            self.actionCompleted.emit(action, count)
            level = "warning" if errors else "success"
            self.notificationRequested.emit(self._status_text, level)
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
            self._clear_preview(keep_errors=True)
        self._can_restore = self._read_can_restore()
        self.failed.emit(self._error_code, self._error_message)
        self.notificationRequested.emit(self._error_message, "error")
        self.stateChanged.emit()

    @Slot()
    def _on_cancelled(self) -> None:
        self._clear_preview()
        self._phase = "cancelled"
        self._status_text = "配对扫描已取消，没有移动任何文件"
        self.cancelled.emit()
        self.stateChanged.emit()

    @Slot()
    def _on_finished(self) -> None:
        self._active_action = ""
        self.stateChanged.emit()

    def _invalidate_preview(self, status: str) -> None:
        self._clear_preview()
        self._phase = "idle"
        self._status_text = status
        self.stateChanged.emit()

    def _clear_preview(self, *, keep_errors: bool = False) -> None:
        self._result = None
        self._items.clear()
        if not keep_errors:
            self._errors = []
        self._progress_current = 0
        self._progress_total = 0

    def _reset_error(self) -> None:
        self._error_code = ""
        self._error_message = ""
        self._errors = []

    def _read_can_restore(self) -> bool:
        try:
            return self._use_case.has_restore()
        except (OSError, ValueError):
            return False

    @staticmethod
    def _error_code_for(exception_name: str) -> str:
        return {
            "FileNotFoundError": "not_found",
            "FileExistsError": "conflict",
            "PermissionError": "permission_denied",
            "RuntimeError": "preview_required",
            "ValueError": "invalid_operation",
            "OSError": "io_error",
        }.get(exception_name, "unexpected")


__all__ = ["CleanupViewModel"]
