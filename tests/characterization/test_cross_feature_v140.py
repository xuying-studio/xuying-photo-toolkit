"""重命名与 XMP 同步组合使用的 v1.4.0 等价测试。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from xuying_toolbox.infrastructure.composition import (
    create_rename_use_case,
    create_xmp_sync_use_case,
)
from xuying_toolbox.infrastructure.metadata.xmp_file import read
from xuying_toolbox.infrastructure.persistence.paths import SupportPaths

MINIMAL_JPEG = b"\xff\xd8\xff\xd9"


class FixedMetadata:
    def capture_time(self, path: Path) -> datetime:
        return datetime.fromtimestamp(path.stat().st_mtime)


def test_xmp_sync_works_before_and_after_uppercase_rename(tmp_path: Path) -> None:
    raw = tmp_path / "B_DSC09252.ARW"
    jpg = tmp_path / "B_DSC09252.JPG"
    sidecar = tmp_path / "B_DSC09252.XMP"
    raw.write_bytes(b"raw-fixture")
    jpg.write_bytes(MINIMAL_JPEG)
    sidecar.write_text(
        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        "<rdf:Description xmp:Rating='1' /></rdf:RDF>",
        encoding="utf-8",
    )
    timestamp = datetime(2026, 7, 25, 10, 0).timestamp()
    for path in (raw, jpg, sidecar):
        os.utime(path, (timestamp, timestamp))
    support = SupportPaths.from_root(tmp_path / "support")
    rename_use_case = create_rename_use_case(support, FixedMetadata())
    xmp_use_case = create_xmp_sync_use_case(support)

    first_sync = xmp_use_case.scan(tmp_path, "RAW → JPG", True, False)
    xmp_use_case.execute(first_sync.operations)
    assert read(jpg).rating == 1

    plan = rename_use_case.scan(tmp_path)
    rename_use_case.execute(plan)
    renamed_raw = next(
        Path(operation.target)
        for operation in plan.operations
        if operation.kind == "照片" and Path(operation.source).suffix == ".ARW"
    )
    renamed_jpg = next(
        Path(operation.target)
        for operation in plan.operations
        if operation.kind == "照片" and Path(operation.source).suffix == ".JPG"
    )
    renamed_sidecar = renamed_raw.with_suffix(".XMP")

    assert renamed_raw.suffix == ".ARW"
    assert renamed_jpg.suffix == ".JPG"
    assert renamed_sidecar.exists()
    renamed_sidecar.write_text(
        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' "
        "xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        "<rdf:Description xmp:Rating='2' /></rdf:RDF>",
        encoding="utf-8",
    )
    second_sync = xmp_use_case.scan(tmp_path, "RAW → JPG", True, False)
    xmp_use_case.execute(second_sync.operations)

    assert read(renamed_jpg).rating == 2
    assert rename_use_case.undo() == 3
    assert raw.exists() and jpg.exists() and sidecar.exists()


def test_xmp_sync_never_changes_raw_bytes(tmp_path: Path) -> None:
    raw = tmp_path / "A001.ARW"
    jpg = tmp_path / "A001.JPG"
    original_raw = b"raw-fixture-must-not-change"
    raw.write_bytes(original_raw)
    jpg.write_bytes(MINIMAL_JPEG)
    from xuying_toolbox.infrastructure.metadata.xmp_file import write

    write(jpg, 5, "Approved")
    xmp_use_case = create_xmp_sync_use_case(SupportPaths.from_root(tmp_path / "support"))
    operations = xmp_use_case.scan(tmp_path, "JPG → RAW", True, True).operations
    xmp_use_case.execute(operations)

    assert raw.read_bytes() == original_raw
    assert raw.with_suffix(".xmp").exists()
