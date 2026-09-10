from pathlib import Path

import pytest

from xuying_toolbox.bootstrap import resolve_qml_root
from xuying_toolbox.domain.errors import AppError, ErrorCode


def test_resolve_qml_root_from_override(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "App.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
    monkeypatch.setenv("XUYING_QML_DIR", str(tmp_path))

    assert resolve_qml_root() == tmp_path.resolve()


def test_invalid_qml_override_uses_structured_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XUYING_QML_DIR", str(tmp_path))

    with pytest.raises(AppError) as caught:
        resolve_qml_root()

    assert caught.value.code is ErrorCode.QML_NOT_FOUND
