"""v1.4.0 时间重命名的脱敏等价测试。"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from xuying_toolbox.domain.models.photo import RenameOperation, RenameScanStats
from xuying_toolbox.domain.services.rename import find_rename_conflicts
from xuying_toolbox.infrastructure.composition import create_rename_use_case
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths


class FixedMetadata:
    def capture_time(self, path: Path) -> datetime:
        return datetime(2026, 7, 25, 10, 0)


def scan(
    folder: Path,
    metadata_reader: FixedMetadata,
    recursive: bool = False,
    progress: object = None,
):
    support = SupportPaths.from_root(folder / "support-default")
    return create_rename_use_case(support, metadata_reader).scan(
        folder,
        recursive=recursive,
        progress=progress,
    )


def execute(plan, support: SupportPaths, progress: object = None) -> Path:
    return create_rename_use_case(support, FixedMetadata()).execute(plan, progress)


def undo(support: SupportPaths, progress: object = None) -> int:
    return create_rename_use_case(support, FixedMetadata()).undo(progress)


def make_pair(root: Path, stem: str = "B_DSC09252") -> None:
    (root / f"{stem}.ARW").write_bytes(b"raw-fixture")
    (root / f"{stem}.JPG").write_bytes(b"jpg-fixture")


def test_non_recursive_and_uppercase_sidecars(tmp_path: Path) -> None:
    make_pair(tmp_path)
    (tmp_path / "B_DSC09252.xmp").write_text("standard", encoding="utf-8")
    (tmp_path / "B_DSC09252.ARW.xmp").write_text("legacy", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    make_pair(nested, "C_DSC00001")

    plan = scan(tmp_path, FixedMetadata())

    assert plan.stats == RenameScanStats(2, 1, 1, 0, 0, 2)
    assert plan.image_count == 2
    assert len([op for op in plan.operations if op.kind == "XMP 侧车"]) == 2
    assert all(Path(op.source).parent == tmp_path for op in plan.operations)
    assert not plan.conflicts


def test_conflict_blocks_execution_before_writing(tmp_path: Path) -> None:
    make_pair(tmp_path)
    (tmp_path / "B_DSC09252.xmp").write_text("source-sidecar", encoding="utf-8")
    (tmp_path / "DSC26-07-25-00001.xmp").write_text("existing", encoding="utf-8")
    plan = scan(tmp_path, FixedMetadata())

    assert plan.conflicts
    with pytest.raises(ValueError):
        execute(plan, SupportPaths.from_root(tmp_path / "support"))
    assert (tmp_path / "B_DSC09252.JPG").exists()


def test_execute_manifest_then_undo_and_new_sidecar(tmp_path: Path) -> None:
    make_pair(tmp_path)
    (tmp_path / "B_DSC09252.xmp").write_text("standard", encoding="utf-8")
    support = SupportPaths.from_root(tmp_path / "support")

    plan = scan(tmp_path, FixedMetadata())
    manifest = execute(plan, support)
    raw = tmp_path / "DSC26-07-25-00001.ARW"
    added = tmp_path / "DSC26-07-25-00001.ARW.xmp"
    added.write_text("new-sidecar", encoding="utf-8")

    assert manifest.exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["state"] == "completed"
    assert raw.exists()
    assert undo(support) == 4
    assert (tmp_path / "B_DSC09252.ARW").exists()
    assert (tmp_path / "B_DSC09252.JPG").exists()
    assert (tmp_path / "B_DSC09252.ARW.xmp").read_text(encoding="utf-8") == "new-sidecar"
    assert not added.exists()


def test_two_phase_failure_restores_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_pair(tmp_path)
    plan = scan(tmp_path, FixedMetadata())
    original_rename = Path.rename
    calls = 0

    def fail_second(source: Path, target: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("fixture failure")
        return original_rename(source, target)

    monkeypatch.setattr(Path, "rename", fail_second)
    with pytest.raises(OSError):
        execute(plan, SupportPaths.from_root(tmp_path / "support"))
    assert all(path.exists() for path in (tmp_path / "B_DSC09252.ARW", tmp_path / "B_DSC09252.JPG"))
    manifests = list((tmp_path / "support" / "rename_backups").glob("*.json"))
    assert len(manifests) == 1
    assert json.loads(manifests[0].read_text(encoding="utf-8"))["state"] == "failed"
    with pytest.raises(FileNotFoundError, match="没有可撤回"):
        undo(SupportPaths.from_root(tmp_path / "support"))


def test_existing_formatted_file_is_kept_and_counter_continues(tmp_path: Path) -> None:
    (tmp_path / "DSC26-07-25-00001.jpg").write_bytes(b"existing")
    (tmp_path / "DSC0001.JPG").write_bytes(b"source")

    plan = scan(tmp_path, FixedMetadata())

    image_operation = next(operation for operation in plan.operations if operation.kind == "照片")
    assert Path(image_operation.target).name == "DSC26-07-25-00002.JPG"
    assert plan.stats.already_named_count == 1


def test_only_exact_five_digit_formatted_names_are_treated_as_existing(tmp_path: Path) -> None:
    (tmp_path / "DSC26-07-25-000001.JPG").write_bytes(b"source")

    plan = scan(tmp_path, FixedMetadata())

    assert plan.stats.already_named_count == 0
    assert plan.image_count == 1


def test_recursive_numbering_uses_global_date_counter_like_v140(tmp_path: Path) -> None:
    first = tmp_path / "A"
    second = tmp_path / "B"
    first.mkdir()
    second.mkdir()
    (first / "DSC26-07-25-00005.JPG").write_bytes(b"existing")
    (first / "IMG0001.JPG").write_bytes(b"one")
    (second / "IMG0002.JPG").write_bytes(b"two")

    plan = scan(tmp_path, FixedMetadata(), recursive=True)
    targets = [
        Path(operation.target).name for operation in plan.operations if operation.kind == "照片"
    ]

    assert targets == ["DSC26-07-25-00006.JPG", "DSC26-07-25-00007.JPG"]


def test_missing_original_number_is_skipped_with_warning(tmp_path: Path) -> None:
    (tmp_path / "portrait.JPG").write_bytes(b"source")

    plan = scan(tmp_path, FixedMetadata())

    assert plan.image_count == 0
    assert plan.stats.skipped_count == 1
    assert len(plan.warnings) == 1


def test_scan_execute_and_undo_progress_finish_at_total(tmp_path: Path) -> None:
    make_pair(tmp_path)
    support = SupportPaths.from_root(tmp_path / "support")
    scan_updates: list[tuple[int, int, str]] = []
    execute_updates: list[tuple[int, int, str]] = []
    undo_updates: list[tuple[int, int, str]] = []

    plan = scan(tmp_path, FixedMetadata(), progress=lambda *args: scan_updates.append(args))
    execute(plan, support, progress=lambda *args: execute_updates.append(args))
    undo(support, progress=lambda *args: undo_updates.append(args))

    for updates in (scan_updates, execute_updates, undo_updates):
        assert updates
        current, total, message = updates[-1]
        assert current == total
        assert total > 0
        assert message


def test_manifest_exists_before_transaction_starts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_pair(tmp_path)
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_rename_use_case(support, FixedMetadata())
    plan = use_case.scan(tmp_path)
    observed_payload: dict[str, object] = {}

    def inspect_manifest(_pairs: list[tuple[Path, Path]], _progress: object) -> None:
        manifests = list(support.rename_backups.glob("*.json"))
        assert len(manifests) == 1
        observed_payload.update(json.loads(manifests[0].read_text(encoding="utf-8")))

    monkeypatch.setattr(use_case.transaction, "run", inspect_manifest)
    use_case.execute(plan)

    assert len(observed_payload["operations"]) == 2


def test_case_only_duplicate_targets_are_blocked() -> None:
    operations = [
        RenameOperation("/fixtures/A001.JPG", "/fixtures/Target.JPG", "照片"),
        RenameOperation("/fixtures/A002.JPG", "/fixtures/target.jpg", "照片"),
    ]

    conflicts = find_rename_conflicts(operations)

    assert len(conflicts) == 1
    assert "多个文件" in conflicts[0]
