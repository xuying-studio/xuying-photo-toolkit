"""XMP 同步预览的虚拟化列表模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from xuying_toolbox.domain.models.photo import SyncOperation


def _rating_text(operation: SyncOperation) -> str:
    if operation.rating is None:
        return "不修改"
    old = str(operation.old_rating) if operation.old_rating > 0 else "无"
    return f"{old} → {operation.rating}"


def _label_text(operation: SyncOperation) -> str:
    if operation.label is None:
        return "不修改"
    return f"{operation.old_label or '无'} → {operation.label}"


class SyncOperationsModel(QAbstractListModel):
    countChanged = Signal()

    ModelDataRole = Qt.ItemDataRole.UserRole + 1
    SourceRole = Qt.ItemDataRole.UserRole + 2
    TargetRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._operations: list[SyncOperation] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._operations)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._operations)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._operations):
            return None
        operation = self._operations[index.row()]
        if role == self.ModelDataRole:
            return {
                "source": Path(operation.source).name,
                "target": Path(operation.target).name,
                "rating": _rating_text(operation),
                "label": _label_text(operation),
                "sourcePath": operation.source,
                "targetPath": operation.target,
            }
        if role == self.SourceRole:
            return operation.source
        if role == self.TargetRole:
            return operation.target
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ModelDataRole: QByteArray(b"modelData"),
            self.SourceRole: QByteArray(b"sourcePath"),
            self.TargetRole: QByteArray(b"targetPath"),
        }

    def set_operations(self, operations: list[SyncOperation]) -> None:
        self.beginResetModel()
        self._operations = list(operations)
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        self.set_operations([])


__all__ = ["SyncOperationsModel"]
