from __future__ import annotations

from pathlib import Path

import pytest

from xuying_toolbox.domain.services.xmp import insert_jpeg_xmp
from xuying_toolbox.infrastructure.composition import create_xmp_sync_use_case
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.presentation.viewmodels import XmpSyncViewModel

MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


@pytest.mark.qml
def test_real_xmp_viewmodel_syncs_sidecar_and_undoes_without_touching_raw(
    qtbot,
    tmp_path: Path,
) -> None:
    photos = tmp_path / "测试照片"
    photos.mkdir()
    jpg = photos / "A001.JPG"
    raw = photos / "A001.ARW"
    jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 5, "Select"))
    raw.write_bytes(b"raw-fixture")
    original_raw = raw.read_bytes()
    support = SupportPaths.from_root(tmp_path / "support")
    view_model = XmpSyncViewModel(create_xmp_sync_use_case(support))
    view_model.folderPath = str(photos)

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.scan()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert view_model.operationCount == 1

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.executeConfirmed()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert raw.read_bytes() == original_raw
    assert raw.with_suffix(".xmp").exists()
    assert view_model.canUndo

    with qtbot.waitSignal(view_model.actionCompleted, timeout=3000):
        view_model.undo()
    qtbot.waitUntil(lambda: not view_model.busy, timeout=2000)
    assert raw.read_bytes() == original_raw
    assert not raw.with_suffix(".xmp").exists()
    assert not view_model.canUndo
