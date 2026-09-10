from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from xuying_toolbox.infrastructure.metadata.exif_reader import ExifMetadataReader


def test_exif_datetime_original_has_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    photo = tmp_path / "A001.JPG"
    photo.write_bytes(b"fixture")
    os.utime(photo, (1_000, 1_000))
    monkeypatch.setattr(
        "xuying_toolbox.infrastructure.metadata.exif_reader.exifread.process_file",
        lambda *_args, **_kwargs: {"EXIF DateTimeOriginal": "2026:09:05 12:34:56"},
    )

    assert ExifMetadataReader().capture_time(photo) == datetime(2026, 9, 5, 12, 34, 56)


def test_broken_exif_falls_back_to_modified_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    photo = tmp_path / "A001.JPG"
    photo.write_bytes(b"fixture")
    timestamp = datetime(2026, 7, 25, 10, 0).timestamp()
    os.utime(photo, (timestamp, timestamp))

    def fail(*_args: object, **_kwargs: object) -> object:
        raise ValueError("broken EXIF")

    monkeypatch.setattr(
        "xuying_toolbox.infrastructure.metadata.exif_reader.exifread.process_file",
        fail,
    )

    assert ExifMetadataReader().capture_time(photo) == datetime.fromtimestamp(timestamp)
