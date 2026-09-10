"""关键词快切实际图片渲染与导出测试。"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from xuying_toolbox.application.tasking import TaskCancelledError
from xuying_toolbox.domain.models.quickcut import ExportMode, NormalizedRect, ProjectSettings
from xuying_toolbox.domain.ports.quickcut_export import QuickCutExportSource
from xuying_toolbox.infrastructure.imaging.quickcut_renderer import QtQuickCutRenderer
from xuying_toolbox.infrastructure.video.ffmpeg_export import FFmpegQuickCutExporter


def _fixture(path: Path) -> None:
    image = QImage(100, 100, QImage.Format.Format_RGB32)
    image.fill(QColor("black"))
    painter = QPainter(image)
    painter.fillRect(40, 30, 20, 5, QColor("red"))
    painter.end()
    assert image.save(str(path), "PNG")


def test_renderer_aligns_source_box_to_target(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _fixture(source)
    settings = ProjectSettings(
        width=100,
        height=100,
        target_rect=NormalizedRect(0.25, 0.45, 0.5, 0.08),
    )

    output = QtQuickCutRenderer().render(
        source,
        NormalizedRect(0.4, 0.3, 0.2, 0.05),
        settings,
    )

    assert (output.width(), output.height()) == (100, 100)
    assert output.pixelColor(50, 50).red() > 200


def test_aligned_png_export_never_overwrites_existing_folder(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _fixture(source)
    settings = ProjectSettings(
        keyword="幸福 定格",
        width=100,
        height=100,
        export_mode=ExportMode.ALIGNED_PNG,
    )
    def fixed_now() -> datetime:
        return datetime(2026, 9, 6, 12, 30, 45)

    def progress(_current: int, _total: int, _message: str) -> None:
        return None

    exporter = FFmpegQuickCutExporter(now=fixed_now)

    first = exporter.export((QuickCutExportSource(source, None),), settings, tmp_path, progress)
    second = exporter.export((QuickCutExportSource(source, None),), settings, tmp_path, progress)

    assert first.directory.name == "幸福-定格-20260906-123045"
    assert second.directory.name == "幸福-定格-20260906-123045-1"
    assert first.files[0].name == "001-source.png"
    assert first.files[0].is_file()


def test_frame_sequence_is_continuous_and_cancel_cleans_partial_output(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _fixture(source)
    settings = ProjectSettings(
        keyword="AGI",
        width=100,
        height=100,
        frames_per_image=3,
        export_mode=ExportMode.FRAME_SEQUENCE,
    )
    exporter = FFmpegQuickCutExporter()
    result = exporter.export(
        (QuickCutExportSource(source, None),),
        settings,
        tmp_path,
        lambda *_args: None,
    )

    assert [path.name for path in result.files] == ["000001.png", "000002.png", "000003.png"]
    assert all(path.is_file() for path in result.files)

    cancelled_destination = tmp_path / "cancelled"

    def cancel_after_first(current: int, _total: int, _message: str) -> None:
        if current >= 1:
            raise TaskCancelledError

    with pytest.raises(TaskCancelledError):
        exporter.export(
            (QuickCutExportSource(source, None),),
            settings,
            cancelled_destination,
            cancel_after_first,
        )
    assert not list(cancelled_destination.iterdir())


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="需要 FFmpeg 与 ffprobe",
)
def test_mp4_export_has_expected_frame_count_and_no_audio(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _fixture(source)
    settings = ProjectSettings(
        keyword="AGI",
        width=100,
        height=100,
        frame_rate=29.97,
        frames_per_image=2,
        export_mode=ExportMode.MP4,
    )
    exporter = FFmpegQuickCutExporter()

    result = exporter.export(
        (QuickCutExportSource(source, None),),
        settings,
        tmp_path,
        lambda current, total, message: None,
    )

    assert result.total_frames == 2
    assert result.files[0].is_file()
    assert not (result.directory / "frames").exists()
    probe = subprocess.run(
        [
            str(shutil.which("ffprobe")),
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=codec_type,avg_frame_rate,nb_read_frames",
            "-of",
            "json",
            str(result.files[0]),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert streams == [
        {
            "codec_type": "video",
            "avg_frame_rate": "30000/1001",
            "nb_read_frames": "2",
        }
    ]
