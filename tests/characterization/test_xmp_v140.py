"""v1.4.0 Adobe XMP 行为的脱敏等价测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import xuying_toolbox.infrastructure.metadata.xmp_transaction as xmp_transaction_module
from xuying_toolbox.domain.services.xmp import (
    XMP_JPEG_HEADER,
    find_jpeg_segment,
    insert_jpeg_xmp,
    make_xmp,
)
from xuying_toolbox.infrastructure.composition import create_xmp_sync_use_case
from xuying_toolbox.infrastructure.filesystem.scanner import preferred_sidecar
from xuying_toolbox.infrastructure.metadata.xmp_file import read, write
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths

MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


def scan_sync(
    folder: Path,
    direction: str,
    sync_rating: bool,
    sync_label: bool,
    recursive: bool = False,
    progress: object = None,
):
    paths = SupportPaths.from_root(folder / "support-default")
    return create_xmp_sync_use_case(paths).scan(
        folder,
        direction,
        sync_rating,
        sync_label,
        recursive=recursive,
        progress=progress,
    )


def build_sync_plan(
    folder: Path,
    direction: str,
    sync_rating: bool,
    sync_label: bool,
):
    return scan_sync(folder, direction, sync_rating, sync_label).operations


def execute_sync(operations, support: SupportPaths, progress: object = None):
    return create_xmp_sync_use_case(support).execute(operations, progress)


def undo_latest_sync(support: SupportPaths, progress: object = None) -> int:
    return create_xmp_sync_use_case(support).undo(progress)


def jpeg_with_xmp(xml: bytes) -> bytes:
    payload = XMP_JPEG_HEADER + xml
    segment_length = len(payload) + 2
    segment = b"\xff\xe1" + segment_length.to_bytes(2, "big") + payload
    return MINIMAL_JPEG[:2] + segment + MINIMAL_JPEG[2:]


def test_raw_reads_xap_single_quotes_and_utf16(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    raw.write_bytes(b"raw-fixture")
    xml = """<?xml version='1.0' encoding='UTF-16'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
         xmlns:xap='http://ns.adobe.com/xap/1.0/'>
  <rdf:Description xap:Rating='2' xap:Label='Red' />
</rdf:RDF>"""
    raw.with_suffix(".xmp").write_bytes(xml.encode("utf-16"))

    assert read(raw).rating == 2
    assert read(raw).label == "Red"


def test_newest_duplicate_raw_sidecar_is_selected(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    raw.write_bytes(b"raw-fixture")
    standard = tmp_path / "A001.xmp"
    legacy = tmp_path / "A001.ARW.xmp"
    standard.write_text("<xmp:Rating>1</xmp:Rating>", encoding="utf-8")
    legacy.write_text("<xmp:Rating>2</xmp:Rating>", encoding="utf-8")
    os.utime(standard, (1_000, 1_000))
    os.utime(legacy, (2_000, 2_000))

    assert preferred_sidecar(raw) == legacy
    assert read(raw).rating == 2


def test_raw_to_jpg_keeps_four_one_star_and_four_two_star(tmp_path: Path) -> None:
    expected: dict[str, int] = {}
    for index in range(8):
        rating = 1 if index < 4 else 2
        stem = f"IMG{index + 1:04d}"
        raw = tmp_path / f"{stem}.ARW"
        jpg = tmp_path / f"{stem}.JPG"
        raw.write_bytes(b"raw-fixture")
        jpg.write_bytes(MINIMAL_JPEG)
        if index == 7:
            xml = f"""<?xml version='1.0' encoding='UTF-16'?>
<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
         xmlns:xap='http://ns.adobe.com/xap/1.0/'>
  <rdf:Description xap:Rating='{rating}' />
</rdf:RDF>"""
            raw.with_suffix(".xmp").write_bytes(xml.encode("utf-16"))
        elif index >= 4:
            raw.with_suffix(".xmp").write_text(
                "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                "xmlns:xap='http://ns.adobe.com/xap/1.0/'>"
                f"<rdf:Description><xap:Rating> {rating} </xap:Rating>"
                "</rdf:Description></rdf:RDF>",
                encoding="utf-8",
            )
        else:
            raw.with_suffix(".xmp").write_text(
                "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
                "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
                f'<rdf:Description xmp:Rating="{rating}" /></rdf:RDF>',
                encoding="utf-8",
            )
        expected[jpg.name] = rating

    result = scan_sync(tmp_path, "RAW → JPG", True, False)
    count, _manifest = execute_sync(result.operations, SupportPaths.from_root(tmp_path / "support"))

    assert count == 8
    assert sorted(operation.rating for operation in result.operations) == [1, 1, 1, 1, 2, 2, 2, 2]
    for name, rating in expected.items():
        assert read(tmp_path / name).rating == rating


def test_sync_pairs_all_raw_jpg_extension_case_combinations(tmp_path: Path) -> None:
    combinations = ((".ARW", ".JPG"), (".ARW", ".jpg"), (".arw", ".JPG"), (".arw", ".jpg"))
    for index, (raw_suffix, jpg_suffix) in enumerate(combinations, start=1):
        stem = f"CASE{index:03d}"
        raw = tmp_path / f"{stem}{raw_suffix}"
        (tmp_path / f"{stem}{jpg_suffix}").write_bytes(MINIMAL_JPEG)
        raw.write_bytes(b"raw-fixture")
        raw.with_suffix(".xmp").write_text("<xmp:Rating>2</xmp:Rating>", encoding="utf-8")

    result = scan_sync(tmp_path, "RAW → JPG", True, False)

    assert result.source_count == 4
    assert result.target_count == 4
    assert result.matched_count == 4
    assert result.marked_count == 4
    assert len(result.operations) == 4


def test_updates_existing_xap_packet_without_duplicate_and_preserves_exif(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    jpg = tmp_path / "A001.JPG"
    raw.write_bytes(b"raw-fixture")
    raw.with_suffix(".xmp").write_text(
        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        "<rdf:Description xmp:Rating='2' /></rdf:RDF>",
        encoding="utf-8",
    )
    existing_xap = (
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        b"xmlns:xap='http://ns.adobe.com/xap/1.0/'>"
        b"<rdf:Description><xap:CreatorTool>Adobe Bridge</xap:CreatorTool>"
        b"</rdf:Description></rdf:RDF>"
    )
    exif_payload = b"Exif\x00\x00camera-metadata"
    exif_segment = b"\xff\xe1" + (len(exif_payload) + 2).to_bytes(2, "big") + exif_payload
    jpeg_content = jpeg_with_xmp(existing_xap)
    jpg.write_bytes(jpeg_content[:2] + exif_segment + jpeg_content[2:])

    operations = build_sync_plan(tmp_path, "RAW → JPG", True, False)
    execute_sync(operations, SupportPaths.from_root(tmp_path / "support"))
    updated = jpg.read_bytes()
    segment = find_jpeg_segment(updated)

    assert segment is not None
    stored_length = int.from_bytes(updated[segment.start + 2 : segment.start + 4], "big")
    assert stored_length == len(segment.payload) + 2
    assert updated.count(XMP_JPEG_HEADER) == 1
    assert exif_payload in updated
    assert b"<xap:CreatorTool>Adobe Bridge</xap:CreatorTool>" in updated
    assert b"<xap:Rating>2</xap:Rating>" in updated


def test_jpg_scan_does_not_read_compressed_pixel_payload(tmp_path: Path, monkeypatch) -> None:
    jpg = tmp_path / "A001.JPG"
    xml = (
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        b"xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        b"<rdf:Description xmp:Rating='2' /></rdf:RDF>"
    )
    jpg.write_bytes(jpeg_with_xmp(xml)[:-2] + b"\xff\xda\x00\x08" + b"pixel-data" * 100_000)

    def fail_full_read(_path: Path) -> bytes:
        raise AssertionError("JPG 读取不应加载整文件")

    monkeypatch.setattr(Path, "read_bytes", fail_full_read)

    assert read(jpg).rating == 2


def test_non_recursive_sync_ignores_marked_nested_folder(tmp_path: Path) -> None:
    nested = tmp_path / "备份"
    nested.mkdir()
    for folder, stem in ((tmp_path, "A001"), (nested, "A002")):
        raw = folder / f"{stem}.ARW"
        raw.write_bytes(b"raw-fixture")
        (folder / f"{stem}.JPG").write_bytes(MINIMAL_JPEG)
        raw.with_suffix(".xmp").write_text("<xmp:Rating>2</xmp:Rating>", encoding="utf-8")

    result = scan_sync(tmp_path, "RAW → JPG", True, False)

    assert result.source_count == 1
    assert result.matched_count == 1
    assert len(result.operations) == 1
    assert Path(result.operations[0].source).parent == tmp_path


def test_jpeg_without_xmp_gets_valid_embedded_packet(tmp_path: Path) -> None:
    jpg = tmp_path / "A001.jpg"
    jpg.write_bytes(MINIMAL_JPEG)

    write(jpg, 4, "Select")

    data = jpg.read_bytes()
    assert data.startswith(b"\xff\xd8\xff\xe1")
    assert XMP_JPEG_HEADER in data
    assert read(jpg).rating == 4
    assert read(jpg).label == "Select"


def test_sync_scan_statistics_and_progress(tmp_path: Path) -> None:
    for number, rating in (("001", 5), ("002", 0)):
        jpg = tmp_path / f"A{number}.jpg"
        raw = tmp_path / f"A{number}.ARW"
        jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, rating, None))
        raw.write_bytes(b"raw-fixture")
    updates: list[tuple[int, int, str]] = []

    result = scan_sync(
        tmp_path,
        "JPG → RAW",
        True,
        False,
        progress=lambda *args: updates.append(args),
    )

    assert result.total_images == 4
    assert result.source_count == 2
    assert result.target_count == 2
    assert result.matched_count == 2
    assert result.marked_count == 1
    assert len(result.operations) == 1
    assert updates[-1][0] == updates[-1][1] == 2


def test_raw_sync_creates_sidecar_and_undo_removes_it(tmp_path: Path) -> None:
    jpg = tmp_path / "A001.jpg"
    raw = tmp_path / "A001.ARW"
    jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 5, "Approved"))
    raw.write_bytes(b"raw-fixture")
    support = SupportPaths.from_root(tmp_path / "support")
    execute_updates: list[tuple[int, int, str]] = []
    undo_updates: list[tuple[int, int, str]] = []

    count, manifest = execute_sync(
        build_sync_plan(tmp_path, "JPG → RAW", True, True),
        support,
        progress=lambda *args: execute_updates.append(args),
    )

    assert count == 1
    assert manifest.exists()
    assert read(raw).rating == 5
    assert read(raw).label == "Approved"
    assert execute_updates[-1][0] == execute_updates[-1][1] == 2
    assert undo_latest_sync(support, progress=lambda *args: undo_updates.append(args)) == 1
    assert undo_updates[-1][0] == undo_updates[-1][1] == 1
    assert not raw.with_suffix(".xmp").exists()


def test_sync_manifest_contains_full_jpeg_backup(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    jpg = tmp_path / "A001.jpg"
    raw.write_bytes(b"raw-fixture")
    raw.with_suffix(".xmp").write_bytes(make_xmp(3, "Review"))
    jpg.write_bytes(MINIMAL_JPEG)

    _, manifest = execute_sync(
        build_sync_plan(tmp_path, "RAW → JPG", True, True),
        SupportPaths.from_root(tmp_path / "support"),
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    backup_name = payload["entries"][0]["backup_name"]

    assert (manifest.parent / backup_name).read_bytes() == MINIMAL_JPEG
    assert payload["entries"][0]["backup_method"] in {"hardlink", "copy"}


def test_partial_sync_failure_rolls_back_automatically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for number in ("001", "002"):
        jpg = tmp_path / f"A{number}.jpg"
        raw = tmp_path / f"A{number}.ARW"
        jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 5, "Select"))
        raw.write_bytes(b"raw-fixture")
    support = SupportPaths.from_root(tmp_path / "support")
    operations = build_sync_plan(tmp_path, "JPG → RAW", True, True)
    original_write = xmp_transaction_module.write
    calls = 0

    def fail_second(path: Path, rating: int | None, label: str | None) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("模拟第二个目标写入失败")
        original_write(path, rating, label)

    monkeypatch.setattr(xmp_transaction_module, "write", fail_second)
    with pytest.raises(OSError, match="第二个目标"):
        execute_sync(operations, support)

    assert not (tmp_path / "A001.xmp").exists()
    assert not (tmp_path / "A002.xmp").exists()
    manifest = next(support.xmp_backups.glob("*/manifest.json"))
    assert json.loads(manifest.read_text(encoding="utf-8"))["undone_at"] is not None


def test_fragment_properties_keep_legacy_regex_compatibility(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    sidecar = tmp_path / "A001.xmp"
    raw.write_bytes(b"raw-fixture")
    sidecar.write_text(
        "<xmp:Rating>3</xmp:Rating><xmp:Label>Blue &amp; Green</xmp:Label>",
        encoding="utf-8",
    )

    assert read(raw).rating == 3
    assert read(raw).label == "Blue & Green"
    write(raw, 4, None)
    assert read(raw).rating == 4


def test_scan_requires_valid_direction_and_selected_field(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="至少选择"):
        scan_sync(tmp_path, "JPG → RAW", False, False)
    with pytest.raises(ValueError, match="方向无效"):
        scan_sync(tmp_path, "JPG ↔ RAW", True, False)


def test_label_can_sync_independently_and_up_to_date_is_counted(tmp_path: Path) -> None:
    first_jpg = tmp_path / "A001.JPG"
    first_raw = tmp_path / "A001.ARW"
    second_jpg = tmp_path / "A002.JPG"
    second_raw = tmp_path / "A002.ARW"
    for jpg, raw in ((first_jpg, first_raw), (second_jpg, second_raw)):
        jpg.write_bytes(MINIMAL_JPEG)
        raw.write_bytes(b"raw-fixture")
    write(first_jpg, 5, "Red")
    write(second_jpg, 2, "Blue")
    write(second_raw, None, "Blue")

    result = scan_sync(tmp_path, "JPG → RAW", False, True)

    assert result.marked_count == 2
    assert result.up_to_date_count == 1
    assert len(result.operations) == 1
    assert result.operations[0].rating is None
    assert result.operations[0].label == "Red"


def test_manifest_exists_before_first_target_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jpg = tmp_path / "A001.JPG"
    raw = tmp_path / "A001.ARW"
    jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 4, None))
    raw.write_bytes(b"raw-fixture")
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_xmp_sync_use_case(support)
    operations = use_case.scan(tmp_path, "JPG → RAW", True, False).operations
    observed = False
    original_write = xmp_transaction_module.write

    def inspect_manifest(path: Path, rating: int | None, label: str | None) -> None:
        nonlocal observed
        manifests = list(support.xmp_backups.glob("*/manifest.json"))
        assert len(manifests) == 1
        observed = True
        original_write(path, rating, label)

    monkeypatch.setattr(xmp_transaction_module, "write", inspect_manifest)
    use_case.execute(operations)

    assert observed is True


def test_undo_restores_original_jpeg_bytes(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    jpg = tmp_path / "A001.JPG"
    original = MINIMAL_JPEG
    raw.write_bytes(b"raw-fixture")
    raw.with_suffix(".xmp").write_bytes(make_xmp(3, "Review"))
    jpg.write_bytes(original)
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_xmp_sync_use_case(support)

    use_case.execute(use_case.scan(tmp_path, "RAW → JPG", True, True).operations)
    assert jpg.read_bytes() != original
    assert use_case.undo() == 1
    assert jpg.read_bytes() == original


def test_undo_refuses_to_overwrite_jpeg_changed_after_sync(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    jpg = tmp_path / "A001.JPG"
    raw.write_bytes(b"raw-fixture")
    raw.with_suffix(".xmp").write_bytes(make_xmp(3, "Review"))
    jpg.write_bytes(MINIMAL_JPEG)
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_xmp_sync_use_case(support)
    use_case.execute(use_case.scan(tmp_path, "RAW → JPG", True, True).operations)

    write(jpg, 5, "ChangedLater")
    changed = jpg.read_bytes()
    with pytest.raises(FileExistsError, match="又被修改"):
        use_case.undo()

    assert jpg.read_bytes() == changed
    assert use_case.has_undo()


def test_undo_refuses_to_delete_new_sidecar_changed_after_sync(tmp_path: Path) -> None:
    jpg = tmp_path / "A001.JPG"
    raw = tmp_path / "A001.ARW"
    jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 4, "Select"))
    raw.write_bytes(b"raw-fixture")
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_xmp_sync_use_case(support)
    use_case.execute(use_case.scan(tmp_path, "JPG → RAW", True, True).operations)

    sidecar = raw.with_suffix(".xmp")
    sidecar.write_bytes(make_xmp(2, "ChangedLater"))
    changed = sidecar.read_bytes()
    with pytest.raises(FileExistsError, match="又被修改"):
        use_case.undo()

    assert sidecar.read_bytes() == changed
    assert use_case.has_undo()


def test_invalid_jpeg_is_never_overwritten(tmp_path: Path) -> None:
    jpg = tmp_path / "broken.JPG"
    original = b"not-a-jpeg"
    jpg.write_bytes(original)

    with pytest.raises(ValueError, match="文件头无效"):
        write(jpg, 5, "Red")

    assert jpg.read_bytes() == original


def test_unknown_xmp_namespace_is_rejected_without_changing_bytes(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    sidecar = tmp_path / "A001.xmp"
    raw.write_bytes(b"raw-fixture")
    original = (
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        b"xmlns:foo='https://example.invalid/custom/'>"
        b"<rdf:Description foo:Rating='2' foo:Creator='keep-me' />"
        b"</rdf:RDF>"
    )
    sidecar.write_bytes(original)

    with pytest.raises(ValueError, match="无法安全更新"):
        write(raw, 5, None)

    assert sidecar.read_bytes() == original


def test_unprefixed_foreign_rating_is_not_treated_as_adobe_xmp(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    sidecar = tmp_path / "A001.xmp"
    raw.write_bytes(b"raw-fixture")
    original = b"<metadata Rating='2' Creator='keep-me' />"
    sidecar.write_bytes(original)

    with pytest.raises(ValueError, match="无法安全更新"):
        write(raw, 5, None)

    assert sidecar.read_bytes() == original


def test_backup_failure_removes_uncommitted_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for number in ("001", "002"):
        jpg = tmp_path / f"A{number}.JPG"
        raw = tmp_path / f"A{number}.ARW"
        jpg.write_bytes(insert_jpeg_xmp(MINIMAL_JPEG, 5, "Select"))
        raw.write_bytes(b"raw-fixture")
        raw.with_suffix(".xmp").write_bytes(make_xmp(1, "Old"))
    support = SupportPaths.from_root(tmp_path / "support")
    use_case = create_xmp_sync_use_case(support)
    operations = use_case.scan(tmp_path, "JPG → RAW", True, True).operations
    original_copy = xmp_transaction_module.shutil.copy2
    calls = 0

    def fail_second_copy(source: Path, target: Path) -> Path:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("模拟第二个备份失败")
        return original_copy(source, target)

    monkeypatch.setattr(xmp_transaction_module.shutil, "copy2", fail_second_copy)

    with pytest.raises(OSError, match="第二个备份"):
        use_case.execute(operations)

    assert list(support.xmp_backups.iterdir()) == []
    assert read(tmp_path / "A001.ARW").rating == 1
    assert read(tmp_path / "A002.ARW").rating == 1
