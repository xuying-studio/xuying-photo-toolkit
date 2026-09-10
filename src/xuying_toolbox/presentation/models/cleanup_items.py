"""配对清理预览的虚拟化列表模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, Signal

from xuying_toolbox.domain.models.photo import CleanupItem


class CleanupItemsModel(QAbstractListModel):
    countChanged = Signal()

    ModelDataRole = Qt.ItemDataRole.UserRole + 1
    PathRole = Qt.ItemDataRole.UserRole + 2
    MissingPairRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: list[CleanupItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._items)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        name = Path(item.path).name
        if role == self.ModelDataRole:
            return {
                "name": name,
                "missing": item.missing_pair_kind,
                "action": "移入系统废纸篓",
                "path": item.path,
            }
        if role == self.PathRole:
            return item.path
        if role == self.MissingPairRole:
            return item.missing_pair_kind
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.ModelDataRole: QByteArray(b"modelData"),
            self.PathRole: QByteArray(b"path"),
            self.MissingPairRole: QByteArray(b"missingPairKind"),
        }

    def set_items(self, items: list[CleanupItem]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        self.set_items([])


__all__ = ["CleanupItemsModel"]
