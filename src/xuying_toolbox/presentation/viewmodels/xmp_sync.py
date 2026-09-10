"""Adobe XMP 同步的 Qt 状态、预览与安全撤回边界。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from xuying_toolbox.application.xmp_sync import XmpSyncUseCase
from xuying_toolbox.domain.models.photo import SyncScanResult
from xuying_toolbox.presentation.models import SyncOperationsModel
from xuying_toolbox.presentation.task_runner import TaskOperation, TaskRunner
from xuying_toolbox.presentation.viewmodels.folder_selection import (
    local_directory_from_url,
)


class XmpSyncViewModel(QObject):
    stateChanged = Signal()
    progressChanged = Signal(int, int, str)
    confirmationRequested = Signal(str, str)
    notificationRequested = Signal(str, str)
    actionCompleted = Signal(str, int)
    failed = Signal(str, str)
    cancelled = Signal()

    def __init__(
        self,
        use_case: XmpSyncUseCase,
        parent: QObject | None = None,
        *,
        task_runner: TaskRunner | None = None,
    ) -> None:
        super().__init__(parent)
        self._use_case = use_case
        self._runner = task_runner or TaskRunner(self)
        self._operations_model = SyncOperationsModel(self)
        self._folder_path = ""
        self._direction = "JPG → RAW"
        self._sync_rating = True
        self._sync_label = True
        self._phase = "idle"
        self._status_text = "请选择照片文件夹"
        self._progress_current = 0
        self._progress_total = 0
        self._result: SyncScanResult | None = None
        self._error_code = ""
        self._error_message = ""
        self._active_action = ""
        self._executed_count = 0
        self._manifest_path = ""
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
        self._invalidate_preview("可以开始只读检查 XMP 标记" if normalized else "请选择照片文件夹")

    @Property(str, notify=stateChanged)
    def direction(self) -> str:
        return self._direction

    @direction.setter
    def direction(self, value: str) -> None:
        if value not in {"JPG → RAW", "RAW → JPG"} or value == self._direction or self.busy:
            return
        self._direction = value
        self._invalidate_preview("同步方向已变更，请重新扫描")

    @Property(bool, notify=stateChanged)
    def syncRating(self) -> bool:
        return self._sync_rating

    @syncRating.setter
    def syncRating(self, value: bool) -> None:
        if value == self._sync_rating or self.busy:
            return
        self._sync_rating = value
        self._invalidate_preview(self._field_status())

    @Property(bool, notify=stateChanged)
    def syncLabel(self) -> bool:
        return self._sync_label

    @syncLabel.setter
    def syncLabel(self, value: bool) -> None:
        if value == self._sync_label or self.busy:
            return
        self._sync_label = value
        self._invalidate_preview(self._field_status())

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
    def operationsModel(self) -> QObject:
        return self._operations_model

    @Property(int, notify=stateChanged)
    def operationCount(self) -> int:
        return self._operations_model.rowCount()

    @Property("QVariantMap", notify=stateChanged)
    def stats(self) -> dict[str, int]:
        result = self._result
        return {
            "totalImages": result.total_images if result else 0,
            "sourceCount": result.source_count if result else 0,
            "targetCount": result.target_count if result else 0,
            "matchedCount": result.matched_count if result else 0,
            "markedCount": result.marked_count if result else 0,
            "upToDateCount": result.up_to_date_count if result else 0,
        }

    @Property(str, notify=stateChanged)
    def errorCode(self) -> str:
        return self._error_code

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property("QStringList", notify=stateChanged)
    def errors(self) -> list[str]:
        return self._error_message.splitlines() if self._error_message else []

    @Property(str, notify=stateChanged)
    def manifestPath(self) -> str:
        return self._manifest_path

    @Property(bool, notify=stateChanged)
    def canScan(self) -> bool:
        return bool(self._folder_path) and (self._sync_rating or self._sync_label) and not self.busy

    @Property(bool, notify=stateChanged)
    def canExecute(self) -> bool:
        return self._result is not None and bool(self._result.operations) and not self.busy

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
            if not self._sync_rating and not self._sync_label:
                self.notificationRequested.emit("至少选择“星标”或“颜色标签”。", "warning")
            return
        folder = self._folder_path
        direction = self._direction
        sync_rating = self._sync_rating
        sync_label = self._sync_label
        self._clear_preview()
        self._reset_error()
        self._start(
            "scan",
            lambda progress: self._use_case.scan(
                folder,
                direction,
                sync_rating,
                sync_label,
                # 前台工具固定只处理当前文件夹。
                recursive=False,
                progress=progress,
            ),
            phase="scanning",
            status="正在只读检查 XMP 星标和颜色标签…",
            cancellable=True,
        )

    @Slot()
    def requestExecute(self) -> None:
        if not self.canExecute or self._result is None:
            return
        target_kind = "RAW 侧车" if self._direction == "JPG → RAW" else "JPG"
        self.confirmationRequested.emit(
            "确认写入 XMP 标记",
            f"将修改 {len(self._result.operations)} 个{target_kind}文件。\n"
            "写入前会整批备份；撤回时若发现后来的修改，会停止并保留备份。",
        )

    @Slot()
    def executeConfirmed(self) -> None:
        if not self.canExecute or self._result is None:
            return
        operations = list(self._result.operations)
        self._executed_count = len(operations)
        self._reset_error()
        self._start(
            "execute",
            lambda progress: self._use_case.execute(operations, progress),
            phase="executing",
            status="正在整批备份并原子写入，此阶段不可中断…",
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
            phase="restoring",
            status="正在检查后续修改并撤回最近同步…",
            cancellable=False,
        )

    @Slot()
    def cancel(self) -> None:
        if self._runner.cancel():
            self._status_text = "正在取消 XMP 扫描…"
            self.stateChanged.emit()
        elif self.busy:
            self.notificationRequested.emit("当前正在备份或写入，完成前不能中断。", "warning")

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
            if not isinstance(result, SyncScanResult):
                self._on_failed("TypeError", "XMP 扫描返回了无效结果。")
                return
            self._result = result
            self._operations_model.set_operations(result.operations)
            self._phase = "ready" if result.operations else "empty"
            self._status_text = (
                f"预览已就绪，找到 {len(result.operations)} 组待同步照片"
                if result.operations
                else "检查完成，没有需要同步的标记"
            )
            self.actionCompleted.emit("scan", len(result.operations))
        elif action == "execute":
            count, manifest = result
            self._manifest_path = str(manifest)
            self._clear_preview()
            self._phase = "completed"
            self._status_text = f"已安全同步 {count} 组 XMP 标记"
            self._can_undo = self._read_can_undo()
            self.actionCompleted.emit("execute", int(count))
            self.notificationRequested.emit("XMP 同步已完成，可以撤回最近一次。", "success")
        elif action == "undo":
            count = int(result)
            self._clear_preview()
            self._phase = "completed"
            self._status_text = f"已撤回 {count} 组 XMP 同步"
            self._can_undo = self._read_can_undo()
            self.actionCompleted.emit("undo", count)
            self.notificationRequested.emit("最近一次 XMP 同步已撤回。", "success")
        self.stateChanged.emit()

    @Slot(str, str)
    def _on_failed(self, exception_name: str, message: str) -> None:
        self._error_code = self._error_code_for(exception_name)
        self._error_message = message or "操作失败，请重试。"
        self._phase = "conflict" if self._error_code == "conflict" else "failed"
        self._status_text = self._error_message
        if self._active_action in {"scan", "execute"}:
            self._clear_preview()
        self._can_undo = self._read_can_undo()
        self.failed.emit(self._error_code, self._error_message)
        self.notificationRequested.emit(self._error_message, "error")
        self.stateChanged.emit()

    @Slot()
    def _on_cancelled(self) -> None:
        self._clear_preview()
        self._phase = "cancelled"
        self._status_text = "XMP 扫描已取消，没有写入任何文件"
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

    def _clear_preview(self) -> None:
        self._result = None
        self._operations_model.clear()
        self._progress_current = 0
        self._progress_total = 0

    def _reset_error(self) -> None:
        self._error_code = ""
        self._error_message = ""

    def _field_status(self) -> str:
        if not self._sync_rating and not self._sync_label:
            return "至少选择“星标”或“颜色标签”"
        return "同步内容已变更，请重新扫描"

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
            "ValueError": "invalid_xmp",
            "OSError": "io_error",
        }.get(exception_name, "unexpected")


__all__ = ["XmpSyncViewModel"]
