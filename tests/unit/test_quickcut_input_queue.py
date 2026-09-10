from pathlib import Path

from xuying_toolbox.application.quickcut.input_queue import QuickCutInputQueueUseCase
from xuying_toolbox.infrastructure.filesystem.quickcut_input import LocalQuickCutInputExpander


def add_inputs(inputs, existing=()):
    return QuickCutInputQueueUseCase(LocalQuickCutInputExpander()).add(inputs, existing)


def test_files_and_directories_filter_without_reading_contents(tmp_path: Path) -> None:
    first = tmp_path / "截图10.JPG"
    second = tmp_path / "截图2.png"
    hidden = tmp_path / ".hidden.jpg"
    unsupported = tmp_path / "notes.txt"
    nested = tmp_path / "nested"
    first.write_bytes(b"not decoded")
    second.write_bytes(b"also not decoded")
    hidden.write_bytes(b"hidden")
    unsupported.write_bytes(b"text")
    nested.mkdir()
    (nested / "deep.jpg").write_bytes(b"deep")

    result = add_inputs([tmp_path])

    assert [path.name for path in result.added] == ["截图2.png", "截图10.JPG"]
    assert result.duplicates == 0
    assert result.ignored == 3


def test_existing_and_canonical_duplicate_paths_are_counted(tmp_path: Path) -> None:
    image = tmp_path / "A1.jpeg"
    image.write_bytes(b"fixture")
    existing = [image]

    result = add_inputs([image, tmp_path / "." / "A1.jpeg"], existing)

    assert result.added == []
    assert result.duplicates == 2
    assert result.ignored == 0


def test_file_inputs_and_case_insensitive_extensions(tmp_path: Path) -> None:
    image = tmp_path / "cover.HEIC"
    image.write_bytes(b"fixture")

    result = add_inputs([image])

    assert result.added == [image.resolve()]
    assert result.duplicates == 0
    assert result.ignored == 0


def test_missing_and_hidden_inputs_are_ignored(tmp_path: Path) -> None:
    result = add_inputs([tmp_path / "missing.jpg", tmp_path / ".hidden-folder"])

    assert result.added == []
    assert result.duplicates == 0
    assert result.ignored == 2
