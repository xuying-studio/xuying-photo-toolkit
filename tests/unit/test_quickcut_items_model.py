"""关键词快切队列模型的移动通知测试。"""

from pathlib import Path

from xuying_toolbox.domain.models.quickcut import QuickCutQueueItem
from xuying_toolbox.presentation.models.quickcut_items import QuickCutItemsModel


def test_move_item_preserves_rows_without_reset(qtbot, tmp_path: Path) -> None:
    model = QuickCutItemsModel()
    items = tuple(
        QuickCutQueueItem(str(index), tmp_path / f"{index}.png")
        for index in range(3)
    )
    model.set_items(items)

    with qtbot.waitSignal(model.rowsMoved, timeout=1000):
        model.move_item(0, 2)

    ids = [model.data(model.index(row, 0), model.IdRole) for row in range(3)]
    assert ids == ["1", "2", "0"]
