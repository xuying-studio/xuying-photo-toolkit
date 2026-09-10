from __future__ import annotations

from pathlib import Path

import pytest

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.infrastructure.filesystem.catalog import LocalPhotoCatalog
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.platform.macos.trash import MacTrashAdapter
from xuying_toolbox.presentation.viewmodels import CleanupViewModel


@pytest.mark.qml
def test_real_cleanup_viewmodel_moves_and_restores_fixture(qtbot, tmp_path: Path) -> None:
    photos = tmp_path / "测试照片"
    trash = tmp_path / "模拟废纸篓"
    photos.mkdir()
    trash.mkdir()
    orphan = photos / "A001.JPG"
    orphan.write_bytes(b"jpg-fixture")
    support = SupportPaths.from_root(tmp_path / "support")

    def fake_send_to_trash(path: str) -> Path:
        target = trash / Path(path).name
        Path(path).rename(target)
        return target

    use_case = CleanupUseCase(
        LocalPhotoCatalog(),
        MacTrashAdapter(support, send_to_trash=fake_send_to_trash),
    )
    view_model = CleanupViewModel(use_case)
    view_model.folderPath = str(photos)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert view_model.itemCount == 1
    assert view_model.canExecute

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.executeConfirmed()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert not orphan.exists()
    assert view_model.canRestore

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.restore()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert orphan.read_bytes() == b"jpg-fixture"
    assert not support.cleanup_undo.exists()
