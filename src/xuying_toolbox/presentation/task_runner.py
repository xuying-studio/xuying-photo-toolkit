"""Qt 后台任务通道；工作线程不直接触碰 QML 对象。"""

from __future__ import annotations

from collections.abc import Callable
from threading import Event
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from xuying_toolbox.application.tasking import TaskCancelledError
from xuying_toolbox.domain.services.progress import ProgressCallback

TaskOperation = Callable[[ProgressCallback], Any]


class _WorkerSignals(QObject):
    progress = Signal(int, int, str)
    succeeded = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()
    finished = Signal()


class _TaskWorker(QRunnable):
    def __init__(self, operation: TaskOperation, *, cancellable: bool) -> None:
        super().__init__()
        self.operation = operation
        self.cancellable = cancellable
        self.signals = _WorkerSignals()
        self._cancel_requested = Event()
        self.setAutoDelete(False)

    def request_cancel(self) -> bool:
        if not self.cancellable:
            return False
        self._cancel_requested.set()
        return True

    def run(self) -> None:
        def report(current: int, total: int, message: str) -> None:
            self._raise_if_cancelled()
            self.signals.progress.emit(current, total, message)

        try:
            self._raise_if_cancelled()
            result = self.operation(report)
            self._raise_if_cancelled()
        except TaskCancelledError:
            self.signals.cancelled.emit()
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(type(exc).__name__, str(exc))
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()

    def _raise_if_cancelled(self) -> None:
        if self.cancellable and self._cancel_requested.is_set():
            raise TaskCancelledError


class TaskRunner(QObject):
    """串行运行一个后台任务，结果通过 Qt 队列信号回主线程。"""

    runningChanged = Signal()
    progress = Signal(int, int, str)
    succeeded = Signal(object)
    failed = Signal(str, str)
    cancelled = Signal()
    finished = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._worker: _TaskWorker | None = None

    @property
    def running(self) -> bool:
        return self._worker is not None

    @property
    def cancellable(self) -> bool:
        return self._worker is not None and self._worker.cancellable

    def start(self, operation: TaskOperation, *, cancellable: bool) -> bool:
        if self._worker is not None:
            return False
        worker = _TaskWorker(operation, cancellable=cancellable)
        worker.signals.progress.connect(self.progress)
        worker.signals.succeeded.connect(self.succeeded)
        worker.signals.failed.connect(self.failed)
        worker.signals.cancelled.connect(self.cancelled)
        worker.signals.finished.connect(self._finish)
        self._worker = worker
        self.runningChanged.emit()
        self._thread_pool.start(worker)
        return True

    def cancel(self) -> bool:
        return self._worker.request_cancel() if self._worker is not None else False

    def _finish(self) -> None:
        self._worker = None
        self.runningChanged.emit()
        self.finished.emit()


__all__ = ["TaskOperation", "TaskRunner"]
