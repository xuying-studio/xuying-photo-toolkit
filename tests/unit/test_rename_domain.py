"""时间重命名核心分组与冲突检测的单元测试。"""

from datetime import datetime
from pathlib import Path

from xuying_toolbox.domain.models.photo import RenameOperation
from xuying_toolbox.domain.services.rename import (
    build_rename_plan,
    extract_original_number,
    extract_stem_prefix,
    find_rename_conflicts,
)


class FixedMetadata:
    """所有照片固定同一拍摄时间，屏蔽时间排序干扰。"""

    def capture_time(self, path: Path) -> datetime:
        return datetime(2026, 11, 17, 10, 0)


def test_extract_original_number_takes_trailing_run() -> None:
    # 回归：带数字的相机前缀（C2_、M4_）不能被误当成编号。
    assert extract_original_number("C2_03712.ARW") == "03712"
    assert extract_original_number("M4_03213.JPG") == "03213"
    assert extract_original_number("DSC03213.ARW") == "03213"
    assert extract_original_number("B_DSC09252.ARW") == "09252"
    assert extract_original_number("portrait.JPG") is None


def test_extract_stem_prefix_separates_camera_identity() -> None:
    assert extract_stem_prefix("C2_03712.ARW") == "C2"
    assert extract_stem_prefix("M4_03213.JPG") == "M4"
    assert extract_stem_prefix("DSC03213.ARW") == "DSC"
    assert extract_stem_prefix("portrait.JPG") == "portrait"


def test_dual_camera_overlapping_numbers_rename_without_conflict(tmp_path: Path) -> None:
    # 两台相机编号重叠：C2_03712 与 M4_03712 是不同照片，RAW+JPG 各自成组。
    for stem in ("C2_03712", "M4_03712"):
        (tmp_path / f"{stem}.ARW").write_bytes(b"raw")
        (tmp_path / f"{stem}.JPG").write_bytes(b"jpg")

    plan = build_rename_plan(sorted(tmp_path.iterdir()), FixedMetadata())

    assert plan.conflicts == []
    targets = {Path(op.target).name for op in plan.operations}
    # 两个编号互不冲突，RAW 与 JPG 配对共享同一编号。
    assert targets == {
        "DSC26-11-17-00001.ARW",
        "DSC26-11-17-00001.JPG",
        "DSC26-11-17-00002.ARW",
        "DSC26-11-17-00002.JPG",
    }


def test_conflict_message_lists_source_files() -> None:
    operations = [
        RenameOperation("/fixtures/A001.ARW", "/fixtures/Target.ARW", "照片"),
        RenameOperation("/fixtures/A002.ARW", "/fixtures/target.arw", "照片"),
    ]

    conflicts = find_rename_conflicts(operations)

    assert len(conflicts) == 1
    assert "A001.ARW" in conflicts[0]
    assert "A002.ARW" in conflicts[0]
