"""关键词快切图片队列的虚拟化列表模型。"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, Qt, QUrl, Signal

from xuying_toolbox.domain.models.quickcut import QuickCutQueueItem


class QuickCutItemsModel(QAbstractListModel):
    countChanged = Signal()

    IdRole = Qt.ItemDataRole.UserRole + 1
    NameRole = Qt.ItemDataRole.UserRole + 2
    PathRole = Qt.ItemDataRole.UserRole + 3
    StateRole = Qt.ItemDataRole.UserRole + 4
    MessageRole = Qt.ItemDataRole.UserRole + 5
    CandidateCountRole = Qt.ItemDataRole.UserRole + 6
    SelectedRole = Qt.ItemDataRole.UserRole + 7
    ThumbnailRole = Qt.ItemDataRole.UserRole + 8

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: tuple[QuickCutQueueItem, ...] = ()
        self._selected_index = -1

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._items)

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        values = {
            self.IdRole: item.id,
            self.NameRole: item.path.name,
            self.PathRole: str(item.path),
            self.StateRole: item.state.value,
            self.MessageRole: item.message,
            self.CandidateCountRole: len(item.candidates),
            self.SelectedRole: index.row() == self._selected_index,
            self.ThumbnailRole: QUrl.fromLocalFile(str(item.path)),
        }
        return values.get(role)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.IdRole: QByteArray(b"itemId"),
            self.NameRole: QByteArray(b"name"),
            self.PathRole: QByteArray(b"path"),
            self.StateRole: QByteArray(b"recognitionState"),
            self.MessageRole: QByteArray(b"message"),
            self.CandidateCountRole: QByteArray(b"candidateCount"),
            self.SelectedRole: QByteArray(b"selected"),
            self.ThumbnailRole: QByteArray(b"thumbnailUrl"),
        }

    def set_items(self, items: tuple[QuickCutQueueItem, ...]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()
        self.countChanged.emit()

    def move_item(self, source: int, target: int) -> None:
        if source == target or not 0 <= source < len(self._items) or not 0 <= target < len(
            self._items
        ):
            return
        destination = target + 1 if source < target else target
        self.beginMoveRows(QModelIndex(), source, source, QModelIndex(), destination)
        mutable = list(self._items)
        item = mutable.pop(source)
        mutable.insert(target, item)
        self._items = tuple(mutable)
        self.endMoveRows()

    def set_selected_index(self, index: int) -> None:
        if index == self._selected_index:
            return
        previous = self._selected_index
        self._selected_index = index
        for row in (previous, index):
            if 0 <= row < len(self._items):
                model_index = self.index(row, 0)
                self.dataChanged.emit(model_index, model_index, [self.SelectedRole])


__all__ = ["QuickCutItemsModel"]
