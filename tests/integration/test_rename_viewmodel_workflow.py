from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from xuying_toolbox.infrastructure.composition import create_rename_use_case
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.presentation.viewmodels import RenameViewModel


class FixedMetadata:
    def capture_time(self, _path: Path) -> datetime:
        return datetime(2026, 9, 6, 10, 0)


@pytest.mark.qml
def test_real_rename_viewmodel_scan_execute_and_undo(qtbot, tmp_path: Path) -> None:
    photos = tmp_path / "测试照片"
    photos.mkdir()
    (photos / "A_IMG0001.ARW").write_bytes(b"raw-fixture")
    (photos / "A_IMG0001.JPG").write_bytes(b"jpg-fixture")
    support = SupportPaths.from_root(tmp_path / "support")
    view_model = RenameViewModel(create_rename_use_case(support, FixedMetadata()))
    view_model.folderPath = str(photos)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert view_model.operationCount == 2
    assert view_model.canExecute

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.executeConfirmed()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert (photos / "DSC26-09-06-00001.ARW").read_bytes() == b"raw-fixture"
    assert (photos / "DSC26-09-06-00001.JPG").read_bytes() == b"jpg-fixture"
    assert view_model.canUndo

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.undo()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert (photos / "A_IMG0001.ARW").read_bytes() == b"raw-fixture"
    assert (photos / "A_IMG0001.JPG").read_bytes() == b"jpg-fixture"
    assert not list(support.rename_backups.glob("*.json"))
