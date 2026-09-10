"""v1.4.0 RAW/JPG 清理行为的脱敏 characterization tests。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from xuying_toolbox.application.cleanup import CleanupUseCase
from xuying_toolbox.domain.models.photo import CleanupItem
from xuying_toolbox.domain.services.cleanup import scan_cleanup
from xuying_toolbox.infrastructure.filesystem.catalog import LocalPhotoCatalog
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths
from xuying_toolbox.platform.macos.trash import MacTrashAdapter, restore_with_finder

MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


def test_scan_pairs_case_insensitive_and_stays_in_current_folder(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "A001.JPG").write_bytes(MINIMAL_JPEG)
    (tmp_path / "a001.ARW").write_bytes(b"raw-fixture")
    orphan = tmp_path / "A002.JPEG"
    orphan.write_bytes(MINIMAL_JPEG)
    (nested / "A002.ARW").write_bytes(b"raw-fixture")

    result = CleanupUseCase(LocalPhotoCatalog(), FakeTrashAdapter()).scan(tmp_path, "JPG")

    assert [Path(item.path) for item in result.items] == [orphan]
    assert result.total_images == 3


def test_use_case_requires_scan_before_execute(tmp_path: Path) -> None:
    adapter = FakeTrashAdapter()
    use_case = CleanupUseCase(LocalPhotoCatalog(), adapter)

    with pytest.raises(RuntimeError, match="先扫描并预览"):
        use_case.execute()


def test_failed_rescan_discards_previous_preview(tmp_path: Path) -> None:
    adapter = FakeTrashAdapter()
    use_case = CleanupUseCase(LocalPhotoCatalog(), adapter)
    (tmp_path / "A001.JPG").write_bytes(MINIMAL_JPEG)
    use_case.scan(tmp_path, "JPG")

    with pytest.raises(FileNotFoundError):
        use_case.scan(tmp_path / "missing", "JPG")
    with pytest.raises(RuntimeError, match="先扫描并预览"):
        use_case.execute()

    assert adapter.items == []

    (tmp_path / "A001.JPG").write_bytes(MINIMAL_JPEG)
    use_case.scan(tmp_path, "JPG")
    use_case.execute()
    assert len(adapter.items) == 1
    with pytest.raises(RuntimeError, match="先扫描并预览"):
        use_case.execute()


def test_mac_adapter_records_before_each_move_and_restores_without_overwrite(
    tmp_path: Path,
) -> None:
    photo_dir = tmp_path / "photos"
    trash_dir = tmp_path / "fake-trash"
    photo_dir.mkdir()
    trash_dir.mkdir()
    photo = photo_dir / "A001.JPG"
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def fake_send_to_trash(path: str) -> None:
        source = Path(path)
        source.rename(trash_dir / source.name)

    adapter = MacTrashAdapter(paths, send_to_trash=fake_send_to_trash)
    moved, errors = adapter.move(
        CleanupUseCase(LocalPhotoCatalog(), FakeTrashAdapter()).scan(photo_dir, "JPG").items
    )

    assert (moved, errors) == (1, [])
    assert not photo.exists()
    payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))
    recovery = Path(payload["items"][0]["recovery_path"])
    assert recovery.exists()

    photo.write_bytes(b"new-user-file")
    restored, restore_errors = adapter.restore()
    assert restored == 0
    assert restore_errors and "未覆盖" in restore_errors[0]
    assert json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))["items"]


def test_mac_adapter_falls_back_to_copy_and_restores_from_fake_trash(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    trash_dir = tmp_path / "fake-trash"
    photo_dir.mkdir()
    trash_dir.mkdir()
    photo = photo_dir / "A001.JPG"
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def fake_send_to_trash(path: str) -> None:
        source = Path(path)
        source.rename(trash_dir / source.name)

    adapter = MacTrashAdapter(paths, send_to_trash=fake_send_to_trash)
    original_link = os.link

    def fail_link(*args: object, **kwargs: object) -> None:
        raise OSError("simulated unsupported hardlink")

    os.link = fail_link  # type: ignore[assignment]
    try:
        moved, errors = adapter.move(
            CleanupUseCase(LocalPhotoCatalog(), FakeTrashAdapter()).scan(photo_dir, "JPG").items
        )
    finally:
        os.link = original_link

    assert (moved, errors) == (1, [])
    payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))
    assert payload["items"][0]["recovery_method"] == "copy"
    restored, restore_errors = adapter.restore()
    assert (restored, restore_errors) == (1, [])
    assert photo.read_bytes() == MINIMAL_JPEG


def test_invalid_cleanup_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="JPG 或 RAW"):
        scan_cleanup([], "PNG")


def test_raw_cleanup_reports_orphan_and_statistics(tmp_path: Path) -> None:
    paired_raw = tmp_path / "A001.ARW"
    paired_jpg = tmp_path / "a001.JPG"
    orphan = tmp_path / "A002.NEF"
    paired_raw.write_bytes(b"raw")
    paired_jpg.write_bytes(MINIMAL_JPEG)
    orphan.write_bytes(b"raw")

    result = CleanupUseCase(LocalPhotoCatalog(), FakeTrashAdapter()).scan(tmp_path, "RAW")

    assert [Path(item.path) for item in result.items] == [orphan]
    assert result.raw_count == 2
    assert result.jpg_count == 1
    assert result.target_count == 2
    assert result.paired_target_count == 1


def test_cleanup_progress_finishes_at_total(tmp_path: Path) -> None:
    (tmp_path / "A001.JPG").write_bytes(MINIMAL_JPEG)
    updates: list[tuple[int, int, str]] = []

    CleanupUseCase(LocalPhotoCatalog(), FakeTrashAdapter()).scan(
        tmp_path,
        "JPG",
        progress=lambda *args: updates.append(args),
    )

    assert updates[-1][0] == updates[-1][1] == 2


def test_recovery_record_exists_before_trash_call(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    trash_dir = tmp_path / "trash"
    photo_dir.mkdir()
    trash_dir.mkdir()
    photo = photo_dir / "A001.JPG"
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def inspect_then_move(path: str) -> None:
        payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))
        assert payload["items"][0]["original_path"] == path
        Path(path).rename(trash_dir / Path(path).name)

    adapter = MacTrashAdapter(paths, send_to_trash=inspect_then_move)
    moved, errors = adapter.move([CleanupItem(str(photo), "RAW")])

    assert (moved, errors) == (1, [])


def test_post_move_error_keeps_recovery_record(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    trash_dir = tmp_path / "trash"
    photo_dir.mkdir()
    trash_dir.mkdir()
    photo = photo_dir / "A001.JPG"
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def move_then_fail(path: str) -> None:
        source = Path(path)
        source.rename(trash_dir / source.name)
        raise OSError("trash returned late failure")

    adapter = MacTrashAdapter(paths, send_to_trash=move_then_fail)
    moved, errors = adapter.move([CleanupItem(str(photo), "RAW")])
    payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))

    assert moved == 0
    assert errors
    assert Path(payload["items"][0]["recovery_path"]).exists()


def test_partial_restore_keeps_only_unfinished_record(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    trash_dir = tmp_path / "trash"
    photo_dir.mkdir()
    trash_dir.mkdir()
    first = photo_dir / "A001.JPG"
    second = photo_dir / "A002.JPG"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    paths = SupportPaths.from_root(tmp_path / "support")

    def fake_trash(path: str) -> None:
        source = Path(path)
        source.rename(trash_dir / source.name)

    adapter = MacTrashAdapter(paths, send_to_trash=fake_trash)
    adapter.move([CleanupItem(str(first), "RAW"), CleanupItem(str(second), "RAW")])
    first.write_bytes(b"new-user-file")
    updates: list[tuple[int, int, str]] = []

    restored, errors = adapter.restore(progress=lambda *args: updates.append(args))
    payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))

    assert restored == 1
    assert errors and "未覆盖" in errors[0]
    assert payload["paths"] == [str(first)]
    assert second.read_bytes() == b"two"
    assert updates[-1][0] == updates[-1][1] == 2


def test_restore_uses_recorded_trash_path_when_backup_is_missing(tmp_path: Path) -> None:
    original_dir = tmp_path / "photos"
    trash_dir = tmp_path / "trash"
    original_dir.mkdir()
    trash_dir.mkdir()
    original = original_dir / "A001.JPG"
    trashed = trash_dir / original.name
    trashed.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")
    paths.cleanup_undo.parent.mkdir(parents=True)
    paths.cleanup_undo.write_text(
        json.dumps(
            {
                "paths": [str(original)],
                "items": [
                    {
                        "original_path": str(original),
                        "trash_path": str(trashed),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    adapter = MacTrashAdapter(paths, restore_fallback=lambda *_args: (False, "unused"))

    restored, errors = adapter.restore()

    assert (restored, errors) == (1, [])
    assert original.read_bytes() == MINIMAL_JPEG
    assert not paths.cleanup_undo.exists()


def test_finder_fallback_does_not_enumerate_entire_trash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = subprocess.CompletedProcess([], 0, stdout="OK\n", stderr="")
    captured: dict[str, str] = {}

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["script"] = command[-1]
        return completed

    monkeypatch.setattr("xuying_toolbox.platform.macos.trash.subprocess.run", fake_run)

    succeeded, error = restore_with_finder(Path("/tmp/照片/A001.JPG"), {})

    assert succeeded is True
    assert error is None
    assert "every item of trash" not in captured["script"]
    assert 'item "A001.JPG" of trash' in captured["script"]


def test_mac_adapter_refuses_symbolic_link_even_if_called_directly(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.JPG"
    outside.write_bytes(b"outside-user-file")
    link = tmp_path / "linked.JPG"
    link.symlink_to(outside)
    paths = SupportPaths.from_root(tmp_path / "support")
    adapter = MacTrashAdapter(
        paths,
        send_to_trash=lambda _path: pytest.fail("符号链接不应进入废纸篓调用"),
    )

    moved, errors = adapter.move([CleanupItem(str(link), "RAW")])

    assert moved == 0
    assert errors and "符号链接" in errors[0]
    assert outside.read_bytes() == b"outside-user-file"
    assert not paths.cleanup_undo.exists()


def test_runtime_error_from_trash_is_structured_and_cleans_pending_backup(tmp_path: Path) -> None:
    photo = tmp_path / "A001.JPG"
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def fail(_path: str) -> None:
        raise RuntimeError("wrapped permission error")

    adapter = MacTrashAdapter(paths, send_to_trash=fail)
    moved, errors = adapter.move([CleanupItem(str(photo), "RAW")])

    assert moved == 0
    assert errors and "wrapped permission error" in errors[0]
    assert photo.exists()
    assert not paths.cleanup_undo.exists()
    assert not (tmp_path / ".摄影文件后期处理助手-恢复备份").exists()


def test_returned_trash_path_is_saved_in_record(tmp_path: Path) -> None:
    photo = tmp_path / "A001.JPG"
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    photo.write_bytes(MINIMAL_JPEG)
    paths = SupportPaths.from_root(tmp_path / "support")

    def move_and_return(path: str) -> Path:
        target = trash_dir / Path(path).name
        Path(path).rename(target)
        return target

    adapter = MacTrashAdapter(paths, send_to_trash=move_and_return)
    moved, errors = adapter.move([CleanupItem(str(photo), "RAW")])
    payload = json.loads(paths.cleanup_undo.read_text(encoding="utf-8"))

    assert (moved, errors) == (1, [])
    assert payload["items"][0]["trash_path"] == str(trash_dir / photo.name)


def test_inode_locator_restores_when_backup_and_recorded_path_are_missing(tmp_path: Path) -> None:
    photos = tmp_path / "photos"
    trash = tmp_path / "trash"
    photos.mkdir()
    trash.mkdir()
    original = photos / "A001.JPG"
    trashed = trash / "renamed-in-trash.JPG"
    trashed.write_bytes(MINIMAL_JPEG)
    stat = trashed.stat()
    paths = SupportPaths.from_root(tmp_path / "support")
    paths.cleanup_undo.parent.mkdir(parents=True)
    paths.cleanup_undo.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "original_path": str(original),
                        "device": stat.st_dev,
                        "inode": stat.st_ino,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def locate(_original: Path, device: int | None, inode: int | None) -> Path | None:
        assert (device, inode) == (stat.st_dev, stat.st_ino)
        return trashed

    adapter = MacTrashAdapter(
        paths,
        restore_fallback=lambda *_args: (False, "unused"),
        trash_locator=locate,
    )

    restored, errors = adapter.restore()

    assert (restored, errors) == (1, [])
    assert original.read_bytes() == MINIMAL_JPEG


class FakeTrashAdapter:
    def __init__(self) -> None:
        self.items: list[object] = []

    def move(
        self,
        items: list[object],
        progress: object = None,
    ) -> tuple[int, list[str]]:
        self.items.extend(items)
        return len(items), []

    def restore(self, progress: object = None) -> tuple[int, list[str]]:
        return 0, []

    def has_restore(self) -> bool:
        return False
