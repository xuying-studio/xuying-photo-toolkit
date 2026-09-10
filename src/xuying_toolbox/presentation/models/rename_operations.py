"""时间重命名预览的虚拟化列表模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from xuying_toolbox.domain.models.photo import RenameOperation


class RenameOperationsModel(QAbstractListModel):
    countChanged = Signal()

    ModelDataRole = Qt.ItemDataRole.UserRole + 1
    SourceRole = Qt.ItemDataRole.UserRole + 2
    TargetRole = Qt.ItemDataRole.UserRole + 3
    KindRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._operations: list[RenameOperation] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._operations)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._operations)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._operations):
            return None
        operation = self._operations[index.row()]
        source_name = Path(operation.source).name
        target_name = Path(operation.target).name
        if role == self.ModelDataRole:
            return {
                "source": source_name,
                "target": target_name,
                "kind": operation.kind,
                "sourcePath": operation.source,
                "targetPath": operation.target,
            }
        if role == self.SourceRole:
            return source_name
        if role == self.TargetRole:
            return target_name
        if role == self.KindRole:
            return operation.kind
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ModelDataRole: QByteArray(b"modelData"),
            self.SourceRole: QByteArray(b"source"),
            self.TargetRole: QByteArray(b"target"),
            self.KindRole: QByteArray(b"kind"),
        }

    def set_operations(self, operations: list[RenameOperation]) -> None:
        self.beginResetModel()
        self._operations = list(operations)
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        self.set_operations([])


__all__ = ["RenameOperationsModel"]
