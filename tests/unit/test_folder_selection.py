"""文件夹拖放只接收本地目录。"""

from pathlib import Path

from PySide6.QtCore import QUrl

from xuying_toolbox.presentation.viewmodels.folder_selection import (
    local_directory_from_url,
)


def test_local_directory_is_accepted(tmp_path: Path) -> None:
    folder, error = local_directory_from_url(QUrl.fromLocalFile(str(tmp_path)))

    assert folder == str(tmp_path)
    assert error is None


def test_file_and_remote_url_are_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "photo.jpg"
    file_path.write_bytes(b"fixture")

    file_folder, file_error = local_directory_from_url(QUrl.fromLocalFile(str(file_path)))
    remote_folder, remote_error = local_directory_from_url(QUrl("https://example.com/photos"))

    assert file_folder == ""
    assert file_error == "请拖入文件夹，不要拖入单个文件。"
    assert remote_folder == ""
    assert remote_error == "请拖入一个本地文件夹。"
