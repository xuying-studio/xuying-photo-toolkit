import os
from pathlib import Path

from xuying_toolbox.domain.models.photo import RAW_EXTENSIONS
from xuying_toolbox.infrastructure.filesystem.scanner import (
    find_sidecars,
    iter_image_files,
    preferred_sidecar,
    sidecar_target_for_rename,
)


def test_all_23_raw_extensions_are_recognized(tmp_path: Path) -> None:
    for index, suffix in enumerate(sorted(RAW_EXTENSIONS)):
        (tmp_path / f"IMG{index:04d}{suffix.upper()}").write_bytes(b"raw-fixture")

    files = iter_image_files(tmp_path)

    assert len(RAW_EXTENSIONS) == 23
    assert len(files) == 23


def test_default_scan_is_non_recursive_and_skips_hidden_files(tmp_path: Path) -> None:
    (tmp_path / "A001.JPG").write_bytes(b"jpg-fixture")
    nested = tmp_path / "备份"
    nested.mkdir()
    (nested / "A002.JPG").write_bytes(b"jpg-fixture")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "A003.JPG").write_bytes(b"jpg-fixture")

    assert [path.name for path in iter_image_files(tmp_path)] == ["A001.JPG"]
    assert [path.name for path in iter_image_files(tmp_path, recursive=True)] == [
        "A001.JPG",
        "A002.JPG",
    ]


def test_sidecar_styles_and_new_targets_are_preserved(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    standard = tmp_path / "A001.XMP"
    legacy = tmp_path / "A001.ARW.xmp"
    raw.write_bytes(b"raw-fixture")
    standard.write_bytes(b"standard")
    legacy.write_bytes(b"legacy")

    assert find_sidecars(raw) == [standard, legacy]
    renamed = tmp_path / "DSC26-09-05-00001.ARW"
    assert sidecar_target_for_rename(raw, renamed, standard).name == "DSC26-09-05-00001.XMP"
    assert sidecar_target_for_rename(raw, renamed, legacy).name == "DSC26-09-05-00001.ARW.xmp"


def test_newest_duplicate_sidecar_is_preferred(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    standard = tmp_path / "A001.xmp"
    legacy = tmp_path / "A001.ARW.xmp"
    raw.write_bytes(b"raw-fixture")
    standard.write_bytes(b"standard")
    legacy.write_bytes(b"legacy")
    standard.touch()
    legacy.touch()
    standard_time = 1_000_000_000
    legacy_time = 2_000_000_000
    os.utime(standard, ns=(standard_time, standard_time))
    os.utime(legacy, ns=(legacy_time, legacy_time))

    assert preferred_sidecar(raw) == legacy


def test_scan_never_follows_symbolic_links(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.JPG"
    outside.write_bytes(b"outside-user-file")
    link = tmp_path / "linked.JPG"
    link.symlink_to(outside)

    assert iter_image_files(tmp_path) == []
    assert outside.read_bytes() == b"outside-user-file"
